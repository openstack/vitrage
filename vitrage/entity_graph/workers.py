# Copyright 2018 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import abc
import threading

import cotyledon
import multiprocessing
import multiprocessing.queues
import os
from oslo_config import cfg
from oslo_log import log
import oslo_messaging
from oslo_utils import uuidutils

from vitrage.api_handler.apis.operational import OperationalApis
from vitrage.entity_graph.graph_persistency import GraphPersistency

from vitrage.api_handler.apis.alarm import AlarmApis
from vitrage.api_handler.apis.event import EventApis
from vitrage.api_handler.apis.rca import RcaApis
from vitrage.api_handler.apis.resource import ResourceApis
from vitrage.api_handler.apis.template import TemplateApis
from vitrage.api_handler.apis.topology import TopologyApis
from vitrage.api_handler.apis.webhook import WebhookApis
from vitrage.common.constants import TemplateStatus as TStatus
from vitrage.common.constants import TemplateTypes as TType
from vitrage.common.exception import VitrageError
from vitrage.coordination import service as coord
from vitrage.entity_graph import EVALUATOR_TOPIC
from vitrage.evaluator.actions.base import ActionMode
from vitrage.evaluator.scenario_evaluator import ScenarioEvaluator
from vitrage.evaluator.scenario_repository import ScenarioRepository
from vitrage.graph.driver.networkx_graph import NXGraph
from vitrage import messaging
from vitrage import rpc as vitrage_rpc
from vitrage import storage

CONF = cfg.CONF
LOG = None

# Supported message types
WAIT_FOR_WORKER_START = 'wait_for_worker_start'
READ_DB_GRAPH = 'read_db_graph'
GRAPH_UPDATE = 'graph_update'
ENABLE_EVALUATION = 'enable_evaluation'
START_EVALUATION = 'start_evaluation'
RELOAD_TEMPLATES = 'reload_templates'
TEMPLATE_ACTION = 'template_action'

ADD = 'add'
DELETE = 'delete'


class GraphWorkersManager(cotyledon.ServiceManager):
    """GraphWorkersManager

     - worker processes
     - the queues used to communicate with these workers
     - methods interface to submit tasks to workers
    """
    def __init__(self):
        super(GraphWorkersManager, self).__init__()
        self._db = None
        self._evaluator_queues = []
        self._template_queues = []
        self._api_queues = []
        self._all_queues = []
        self.register_hooks(on_terminate=self._force_stop)
        self.add_evaluator_workers()
        self.add_api_workers()

    def add_evaluator_workers(self):
        """Add evaluator workers

        Evaluator workers receive all graph updates, hence are updated.
        Each evaluator worker holds an enabled scenario-evaluator and process
        every change.
        Each worker's scenario-evaluator runs different template scenarios.
        Interface to these workers is:
        submit_graph_update(..)
        submit_start_evaluations(..)
        submit_evaluators_reload_templates(..)
        """
        if self._evaluator_queues:
            raise VitrageError('add_evaluator_workers called more than once')
        workers = CONF.evaluator.workers
        queues = [multiprocessing.JoinableQueue() for i in range(workers)]
        self.add(EvaluatorWorker,
                 args=(queues, workers),
                 workers=workers)
        self._evaluator_queues = queues
        self._all_queues.extend(queues)

    def add_api_workers(self):
        """Add Api workers

        Api workers receive all graph updates, hence are updated.
        Each template worker holds a disabled scenario-evaluator that does
        not process changes.
        These also hold a rpc server and process the incoming Api calls
        """
        if self._api_queues:
            raise VitrageError('add_api_workers called more than once')
        workers = CONF.api.workers
        queues = [multiprocessing.Queue() for i in range(workers)]
        self.add(ApiWorker, args=(queues,), workers=workers)
        self._api_queues = queues
        self._all_queues.extend(queues)

    def submit_graph_update(self, before, current, is_vertex, *args, **kwargs):
        """Graph update all workers

        This method is subscribed to entity graph changes.
        Per each change in the main entity graph, this method will notify
         each of the workers, causing them to update their own graph.
        """
        self._submit_and_wait(
            self._all_queues,
            (GRAPH_UPDATE, before, current, is_vertex))

    def submit_start_evaluations(self):
        """Enable scenario-evaluator in all evaluator workers

        Enables the worker's scenario-evaluator, and run it on the entire graph
        """
        self._submit_and_wait(self._evaluator_queues, (START_EVALUATION,))

    def submit_enable_evaluations(self):
        """Enable scenario-evaluator in all evaluator workers

        Only enables the worker's scenario-evaluator, without traversing
        """
        self._submit_and_wait(self._evaluator_queues, (ENABLE_EVALUATION,))

    def submit_evaluators_reload_templates(self):
        """Recreate the scenario-repository in all evaluator workers

        So that new/deleted templates are added/removed
        """
        self._submit_and_wait(self._evaluator_queues, (RELOAD_TEMPLATES,))

    def submit_read_db_graph(self):
        """Initialize the worker graph from database snapshot

        So that new/deleted templates are added/removed
        """
        LOG.info("Worker processes - loading graph...")
        self._submit_and_wait(self._all_queues, (READ_DB_GRAPH,))
        LOG.info("Worker processes - graph is ready")

    def wait_for_worker_start(self):
        """Wait for responses from all workers

        So that new/deleted templates are added/removed
        """
        self._submit_and_wait(self._all_queues, (WAIT_FOR_WORKER_START,))
        global LOG
        if not LOG:
            LOG = log.getLogger(__name__)
        LOG.info("Worker processes - ready!")

    def submit_template_event(self, event):
        """Template worker to load the new/deleted template

        Load the template to scenario-evaluator and run it on the entire graph
        """
        template_action = event.get(TEMPLATE_ACTION)

        if not self._db:
            self._db = storage.get_connection_from_config()

        if template_action == ADD:
            templates = self._db.templates.query(status=TStatus.LOADING)
            new_status = TStatus.ACTIVE
            action_mode = ActionMode.DO
        elif template_action == DELETE:
            templates = self._db.templates.query(status=TStatus.DELETING)
            new_status = TStatus.DELETED
            action_mode = ActionMode.UNDO
        else:
            raise VitrageError('Invalid template_action %s' % template_action)

        # Template event will be handled by a single evaluator worker
        self._submit_and_wait(
            [self._evaluator_queues[0]],
            (
                TEMPLATE_ACTION,
                [t.name for t in templates
                 if t.template_type == TType.STANDARD],
                action_mode,
            ))

        for t in templates:
            self._db.templates.update(t.uuid, 'status', new_status)

    @staticmethod
    def _submit_and_wait(queues, payload):
        for q in queues:
            q.put(payload)
        for q in queues:
            if isinstance(q, multiprocessing.queues.JoinableQueue):
                q.join()

    @staticmethod
    def _force_stop():
        os._exit(0)


class GraphCloneWorkerBase(coord.Service):
    def __init__(self,
                 worker_id,
                 task_queues):
        super(GraphCloneWorkerBase, self).__init__(worker_id)
        self._task_queue = task_queues[worker_id]
        self._entity_graph = NXGraph()

    name = 'GraphCloneWorkerBase'

    @abc.abstractmethod
    def _init_instance(self):
        """This method is executed in the newly created process"""
        raise NotImplementedError

    def run(self):
        global LOG
        if not LOG:
            LOG = log.getLogger(__name__)
        super(GraphCloneWorkerBase, self).run()
        self._entity_graph.notifier._subscriptions = []  # Quick n dirty
        self._init_instance()
        if self._entity_graph.num_vertices():
            LOG.info("%s - Started %s (%s vertices)", self.__class__.__name__,
                     self.worker_id, self._entity_graph.num_vertices())
        else:
            LOG.info("%s - Started empty %s", self.__class__.__name__,
                     self.worker_id)
        self._read_queue()

    def _read_queue(self):
        LOG.debug("%s - reading queue %s",
                  self.__class__.__name__, self.worker_id)
        while True:
            try:
                next_task = self._task_queue.get()
                self.do_task(next_task)
            except Exception:
                LOG.exception("Graph may not be in sync.")
            if isinstance(self._task_queue,
                          multiprocessing.queues.JoinableQueue):
                self._task_queue.task_done()

    def do_task(self, task):
        action = task[0]
        if action == GRAPH_UPDATE:
            (action, before, current, is_vertex) = task
            self._graph_update(before, current, is_vertex)
        elif action == READ_DB_GRAPH:
            self._read_db_graph()
        elif action == WAIT_FOR_WORKER_START:
            # Nothing to do, manager is just verifying this worker is alive
            pass

    def _graph_update(self, before, current, is_vertex):
        if current:
            if is_vertex:
                self._entity_graph.add_vertex(current)
            else:
                self._entity_graph.add_edge(current)
        else:
            if is_vertex:
                self._entity_graph.remove_vertex(before)
            else:
                self._entity_graph.remove_edge(before)

    def _read_db_graph(self):
        db = storage.get_connection_from_config()
        graph_snapshot = db.graph_snapshots.query()
        NXGraph.read_gpickle(graph_snapshot.graph_snapshot, self._entity_graph)
        GraphPersistency.do_replay_events(db, self._entity_graph,
                                          graph_snapshot.event_id)
        self._entity_graph.ready = True


class EvaluatorWorker(GraphCloneWorkerBase):
    def __init__(self,
                 worker_id,
                 task_queues,
                 workers_num):
        super(EvaluatorWorker, self).__init__(
            worker_id, task_queues)
        self._workers_num = workers_num
        self._evaluator = None

    name = 'EvaluatorWorker'

    def _init_instance(self):
        scenario_repo = ScenarioRepository(self.worker_id,
                                           self._workers_num)
        actions_callback = messaging.VitrageNotifier(
            publisher_id='vitrage_evaluator',
            topics=[EVALUATOR_TOPIC]).notify
        self._evaluator = ScenarioEvaluator(
            self._entity_graph,
            scenario_repo,
            actions_callback,
            enabled=False)
        self._evaluator.scenario_repo.log_enabled_scenarios()

    def do_task(self, task):
        super(EvaluatorWorker, self).do_task(task)
        action = task[0]
        if action == START_EVALUATION:
            # fresh init (without snapshot) requires iterating the graph
            self._evaluator.run_evaluator()
        elif action == ENABLE_EVALUATION:
            # init with a snapshot does not require iterating the graph
            self._evaluator.enabled = True
        elif action == RELOAD_TEMPLATES:
            self._reload_templates()
        elif action == TEMPLATE_ACTION:
            (action, template_names, action_mode) = task
            self._template_action(template_names, action_mode)

    def _reload_templates(self):
        LOG.info("reloading evaluator scenarios")
        scenario_repo = ScenarioRepository(self.worker_id,
                                           self._workers_num)
        self._evaluator.scenario_repo = scenario_repo
        self._evaluator.scenario_repo.log_enabled_scenarios()

    def _template_action(self, template_names, action_mode):
        # Here, we create a temporary ScenarioRepo to execute the needed
        # templates. Once _reload_templates is called, it will create a
        # non temporary ScenarioRepo, to replace this one
        scenario_repo = ScenarioRepository()
        for s in scenario_repo._all_scenarios:
            s.enabled = False
            for template_name in template_names:
                if s.id.startswith(template_name):
                    s.enabled = True
        self._evaluator.scenario_repo = scenario_repo
        self._evaluator.scenario_repo.log_enabled_scenarios()
        self._evaluator.run_evaluator(action_mode)


class ApiWorker(GraphCloneWorkerBase):

    name = 'ApiWorker'

    def _init_instance(self):
        notifier = messaging.VitrageNotifier("vitrage.api",
                                             [EVALUATOR_TOPIC])
        db = storage.get_connection_from_config()
        transport = messaging.get_rpc_transport()
        target = oslo_messaging.Target(topic=CONF.rpc_topic,
                                       server=uuidutils.generate_uuid())
        self.api_lock = threading.RLock()

        endpoints = [
            TopologyApis(self._entity_graph, self.api_lock),
            AlarmApis(self._entity_graph, self.api_lock, db),
            RcaApis(self._entity_graph, self.api_lock, db),
            ResourceApis(self._entity_graph, self.api_lock),
            TemplateApis(notifier, db),
            EventApis(),
            WebhookApis(db),
            OperationalApis(self._entity_graph),
        ]

        server = vitrage_rpc.get_server(target, endpoints, transport)

        server.start()

    def do_task(self, task):
        try:
            self.api_lock.acquire()
            super(ApiWorker, self).do_task(task)
        finally:
            self.api_lock.release()
