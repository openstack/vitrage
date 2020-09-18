# Copyright 2016 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import queue
import time

from oslo_config import cfg
from testtools import matchers

from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.entity_graph.consistency.consistency_enforcer \
    import ConsistencyEnforcer
from vitrage.entity_graph.processor.processor import Processor
from vitrage.evaluator.scenario_evaluator import ScenarioEvaluator
from vitrage.evaluator.scenario_repository import ScenarioRepository
from vitrage.graph.driver.networkx_graph import NXGraph
from vitrage.tests.functional.base import TestFunctionalBase
from vitrage.tests.functional.test_configuration import TestConfiguration
from vitrage.tests.mocks import utils
from vitrage.utils import datetime


# noinspection PyProtectedMember
class TestConsistencyFunctional(TestFunctionalBase, TestConfiguration):

    CONSISTENCY_OPTS = [
        cfg.IntOpt('min_time_to_delete',
                   default=1,
                   min=1),
    ]

    EVALUATOR_OPTS = [
        cfg.StrOpt('templates_dir',
                   default=utils.get_resources_dir() +
                   '/templates/consistency',
                   ),
        cfg.StrOpt('equivalences_dir',
                   default='equivalences',
                   ),
        cfg.StrOpt('notifier_topic',
                   default='vitrage.evaluator',
                   ),
    ]

    def setUp(self):
        super(TestConsistencyFunctional, self).setUp()
        self.conf_reregister_opts(self.CONSISTENCY_OPTS, 'consistency')
        self.conf_reregister_opts(self.EVALUATOR_OPTS, 'evaluator')
        self.add_db()
        self.load_datasources()
        self.graph = NXGraph("Entity Graph")
        self.processor = Processor(self.graph)

        self.event_queue = queue.Queue()

        def actions_callback(event_type, data):
            """Mock notify method

            Mocks vitrage.messaging.VitrageNotifier.notify(event_type, data)

            :param event_type: is currently always the same and is ignored
            :param data:
            """
            self.event_queue.put(data)

        def actions_callback_consistency(data):
            for e in data:
                self.event_queue.put(e)

        scenario_repo = ScenarioRepository()
        self.evaluator = ScenarioEvaluator(self.processor.entity_graph,
                                           scenario_repo,
                                           actions_callback)
        self.consistency_enforcer = ConsistencyEnforcer(
            self.processor.entity_graph,
            actions_callback_consistency)

    def test_periodic_process(self):
        # Setup
        consistency_interval = self.conf.datasources.snapshots_interval
        self._periodic_process_setup_stage(consistency_interval)
        self._add_alarms_by_type(consistency_interval=consistency_interval,
                                 alarm_type='prometheus')

        # Action
        time.sleep(2 * consistency_interval + 1)
        self.consistency_enforcer.periodic_process()
        self._process_events()

        # Test Assertions
        instance_vertices = self.processor.entity_graph.get_vertices({
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE
        })
        deleted_instance_vertices = \
            self.processor.entity_graph.get_vertices({
                VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE,
                VProps.VITRAGE_IS_DELETED: True
            })
        self.assertThat(instance_vertices,
                        matchers.HasLength(self.NUM_INSTANCES - 3))

        # number of resources:
        # number of vertices - 3 (deleted instances)
        # number of nics - 1
        # number of volumes - 1
        # number of prometheus alarms - 1
        self.assertThat(self.processor.entity_graph.get_vertices(),
                        matchers.HasLength(
                            # 3 instances deleted
                            self._num_total_expected_vertices() - 3 +
                            3 - 1 +     # one nic deleted
                            3 - 1 +     # one cinder.volume deleted
                            3 - 1)      # one prometheus deleted
                        )
        self.assertThat(deleted_instance_vertices, matchers.HasLength(3))

        # one nic was deleted, one marked as deleted, one untouched
        # same for cinder.volume
        self._assert_vertices_status(EntityCategory.RESOURCE, 'nic', 2, 1)
        self._assert_vertices_status(
            EntityCategory.RESOURCE, 'cinder.volume', 2, 1)

        # one prometheus deleted, other two are untouched
        # prometheus vertices should not be marked as deleted, since the
        # datasource did not ask to delete outdated vertices.
        self._assert_vertices_status(EntityCategory.ALARM, 'prometheus', 2, 0)

    def test_should_delete_vertex(self):
        # should be deleted because the static datasource asks to delete its
        # outdated vertices
        static_vertex = {VProps.VITRAGE_DATASOURCE_NAME: 'static'}
        self.assertTrue(
            self.consistency_enforcer._should_delete_vertex(static_vertex))

        # should be deleted because the cinder datasource asks to delete its
        # outdated vertices
        volume_vertex = {VProps.VITRAGE_DATASOURCE_NAME: 'cinder.volume'}
        self.assertTrue(
            self.consistency_enforcer._should_delete_vertex(volume_vertex))

        # should not be deleted because the prometheus datasource does not ask
        # to delete its outdated vertices
        prometheus_vertex = {VProps.VITRAGE_DATASOURCE_NAME: 'prometheus'}
        self.assertFalse(
            self.consistency_enforcer._should_delete_vertex(prometheus_vertex))

        # should be deleted because it is a placeholder
        placeholder_vertex = {VProps.VITRAGE_IS_PLACEHOLDER: True,
                              VProps.VITRAGE_TYPE: 'prometheus'}
        self.assertTrue(self.consistency_enforcer.
                        _should_delete_vertex(placeholder_vertex))

        # should not be deleted because it is an openstack.cluster
        cluster_vertex = {VProps.VITRAGE_IS_PLACEHOLDER: True,
                          VProps.VITRAGE_TYPE: 'openstack.cluster'}
        self.assertFalse(self.consistency_enforcer._should_delete_vertex(
            cluster_vertex))

        vertices = [static_vertex, volume_vertex, prometheus_vertex,
                    placeholder_vertex, cluster_vertex]
        vertices_to_mark_deleted = self.consistency_enforcer.\
            _filter_vertices_to_be_marked_as_deleted(vertices)

        self.assertThat(vertices_to_mark_deleted, matchers.HasLength(3))
        self.assertTrue(static_vertex in vertices_to_mark_deleted)
        self.assertTrue(placeholder_vertex in vertices_to_mark_deleted)
        self.assertTrue(volume_vertex in vertices_to_mark_deleted)
        self.assertFalse(prometheus_vertex in vertices_to_mark_deleted)
        self.assertFalse(cluster_vertex in vertices_to_mark_deleted)

    def _assert_vertices_status(self, category, vitrage_type,
                                num_vertices, num_marked_deleted):
        vertices = \
            self.processor.entity_graph.get_vertices({
                VProps.VITRAGE_CATEGORY: category,
                VProps.VITRAGE_TYPE: vitrage_type,
            })
        self.assertThat(vertices, matchers.HasLength(num_vertices))

        marked_deleted_vertices = \
            self.processor.entity_graph.get_vertices({
                VProps.VITRAGE_CATEGORY: category,
                VProps.VITRAGE_TYPE: vitrage_type,
                VProps.VITRAGE_IS_DELETED: True
            })
        self.assertThat(marked_deleted_vertices,
                        matchers.HasLength(num_marked_deleted))

    def _periodic_process_setup_stage(self, consistency_interval):
        self._create_processor_with_graph(processor=self.processor)
        current_timestamp = datetime.utcnow()
        current_time = str(datetime.datetime_delta(0, current_timestamp))
        time_1_5 = str(datetime.datetime_delta(
            1 * consistency_interval, current_timestamp))
        time_2 = str(datetime.datetime_delta(
            2 * consistency_interval + 1, current_timestamp))

        # set all vertices to be have timestamp that consistency won't get
        self._update_timestamp(
            self.processor.entity_graph.get_vertices(),
            time_1_5)

        # check number of instances in graph
        instance_vertices = self.processor.entity_graph.get_vertices({
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE
        })
        self.assertThat(instance_vertices,
                        matchers.HasLength(self.NUM_INSTANCES))

        # set current timestamp of part of the instances
        self._update_timestamp(instance_vertices[0:3], current_time)

        # set part of the instances as deleted
        for i in range(3, 6):
            instance_vertices[i][VProps.VITRAGE_IS_DELETED] = True
            self.processor.entity_graph.update_vertex(instance_vertices[i])

        # set part of the instances as deleted
        for i in range(6, 9):
            instance_vertices[i][VProps.VITRAGE_IS_DELETED] = True
            instance_vertices[i][VProps.VITRAGE_SAMPLE_TIMESTAMP] = time_2
            self.processor.entity_graph.update_vertex(instance_vertices[i])

        self._add_resources_by_type(consistency_interval=consistency_interval,
                                    datasource_name='static',
                                    resource_type='nic')
        self._add_resources_by_type(consistency_interval=consistency_interval,
                                    datasource_name='cinder.volume',
                                    resource_type='cinder.volume')

    def _update_timestamp(self, lst, timestamp):
        for vertex in lst:
            vertex[VProps.VITRAGE_SAMPLE_TIMESTAMP] = str(timestamp)
            self.processor.entity_graph.update_vertex(vertex)

    def _process_events(self):
        num_retries = 0
        while True:
            if self.event_queue.empty():
                time.sleep(0.3)

            if not self.event_queue.empty():
                time.sleep(1)
                count = 0
                while not self.event_queue.empty():
                    count += 1
                    data = self.event_queue.get()
                    if isinstance(data, list):
                        for event in data:
                            self.processor.process_event(event)
                    else:
                        self.processor.process_event(data)
                return

            num_retries += 1
            if num_retries == 30:
                return

    def _add_resources_by_type(self, consistency_interval, resource_type,
                               datasource_name):
        def _create_resource_by_type(v_id, v_type, ds_name, timestamp,
                                     is_deleted=False):
            return self._create_resource(
                vitrage_id=v_id, resource_type=v_type, datasource_name=ds_name,
                sample_timestamp=timestamp, is_deleted=is_deleted)

        self._add_entities_with_different_timestamps(
            consistency_interval=consistency_interval,
            create_func=_create_resource_by_type,
            category=EntityCategory.RESOURCE,
            datasource_name=datasource_name, resource_type=resource_type)

    def _add_alarms_by_type(
            self, consistency_interval, alarm_type):
        def _create_alarm_by_type(v_id, v_type, ds_name, timestamp,
                                  is_deleted=False):
            return self._create_alarm(
                vitrage_id=v_id, alarm_type=v_type, datasource_name=ds_name,
                project_id=None, vitrage_resource_project_id=None,
                metadata=None, vitrage_sample_timestamp=timestamp,
                is_deleted=is_deleted)

        self._add_entities_with_different_timestamps(
            consistency_interval=consistency_interval,
            create_func=_create_alarm_by_type,
            category=EntityCategory.ALARM,
            datasource_name=alarm_type, resource_type=alarm_type)

    def _add_entities_with_different_timestamps(self, consistency_interval,
                                                create_func,
                                                category,
                                                datasource_name,
                                                resource_type):
        # add resources to the graph:
        # - updated_resource
        # - outdated_resource with an old timestamp
        # - deleted_resource with an old timestamp and is_deleted==true

        future_timestamp = str(datetime.datetime_delta(
            2 * consistency_interval))
        past_timestamp = str(datetime.datetime_delta(
            -2 * consistency_interval + 1))

        updated_resource = create_func(
            v_id=resource_type + '1234', v_type=resource_type,
            ds_name=datasource_name, timestamp=future_timestamp)
        outdated_resource = create_func(
            v_id=resource_type + '5678', v_type=resource_type,
            ds_name=datasource_name, timestamp=past_timestamp)
        deleted_resource = create_func(
            v_id=resource_type + '9999', v_type=resource_type,
            ds_name=datasource_name, timestamp=past_timestamp, is_deleted=True)

        self.graph.add_vertex(updated_resource)
        self.graph.add_vertex(outdated_resource)
        self.graph.add_vertex(deleted_resource)

        # get the list of vertices
        resource_vertices = self.processor.entity_graph.get_vertices({
            VProps.VITRAGE_CATEGORY: category,
            VProps.VITRAGE_TYPE: resource_type
        })

        self.assertThat(resource_vertices, matchers.HasLength(3),
                        'Wrong number of vertices of type %s', resource_type)
