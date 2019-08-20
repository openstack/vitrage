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
from collections import defaultdict
import threading
import time

from oslo_config import cfg
from oslo_log import log
import oslo_messaging
from vitrage.utils.datetime import format_utcnow

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps

from vitrage.datasources.consistency import CONSISTENCY_DATASOURCE
from vitrage.datasources import utils
from vitrage import messaging

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class DriverExec(object):

    def __init__(self, process_output_func, persist, graph):
        self.graph = graph
        self.process_output_func = process_output_func
        self.persist = persist

    def snapshot_get_all(self, action=DatasourceAction.INIT_SNAPSHOT):
        driver_names = CONF.datasources.types
        LOG.info('get_all starting for %s', driver_names)
        t1 = time.time()
        events_count = 0
        for d in driver_names:
            events_count += self.get_all(d, action)
        LOG.info('get_all and processing took %s for %s events',
                 time.time() - t1, events_count)
        self.persist.store_graph()

    def get_all(self, driver_name, action):
        try:
            LOCK_BY_DRIVER.acquire(driver_name)
            driver = utils.get_drivers_by_name([driver_name])[0]
            LOG.info("run driver get_all: %s", driver_name)
            now = format_utcnow()
            events = driver.get_all(action)
            count = self.process_output_func(events)
            LOG.info("run driver get_all: %s done (%s events)",
                     driver_name, count)

            if driver.should_delete_outdated_entities():
                vertices_to_delete = \
                    self._find_vertices_to_delete(driver_name, now)
                if vertices_to_delete:
                    delete_events = self._to_events(vertices_to_delete)
                    count_deleted = self.process_output_func(delete_events)
                    LOG.info("run driver delete outdated vertices: %s done "
                             "(%s events)", driver_name, count_deleted)
                    count += count_deleted
            return count
        except Exception:
            LOG.exception("run driver get_all: %s Failed", driver_name)
        finally:
            LOCK_BY_DRIVER.release(driver_name)
        return 0

    def get_changes(self, driver_name):
        if not LOCK_BY_DRIVER.acquire(driver_name, blocking=False):
            LOG.info("%s get_changes canceled during get_all execution",
                     driver_name)
            return 0
        try:
            driver = utils.get_drivers_by_name([driver_name])[0]
            LOG.info("run driver get_changes: %s", driver_name)
            events = driver.get_changes(DatasourceAction.UPDATE)
            count = self.process_output_func(events)
            LOG.info("run driver get_changes: %s done (%s events)",
                     driver_name, count)
            return count
        except Exception:
            LOG.exception("run driver get_changes: %s Failed", driver_name)
        finally:
            LOCK_BY_DRIVER.release(driver_name)
        return 0

    @staticmethod
    def _to_events(vertices):
        return (
            {
                DSProps.ENTITY_TYPE: CONSISTENCY_DATASOURCE,
                DSProps.DATASOURCE_ACTION: DatasourceAction.UPDATE,
                DSProps.SAMPLE_DATE: format_utcnow(),
                DSProps.EVENT_TYPE: GraphAction.DELETE_ENTITY,
                VProps.VITRAGE_ID: vertex[VProps.VITRAGE_ID],
                VProps.ID: vertex.get(VProps.ID, None),
                VProps.VITRAGE_TYPE: vertex[VProps.VITRAGE_TYPE],
                VProps.VITRAGE_CATEGORY: vertex[VProps.VITRAGE_CATEGORY],
                VProps.IS_REAL_VITRAGE_ID: True
            }
            for vertex in vertices
        )

    def _find_vertices_to_delete(self, driver_name, now):
        query = {
            'and': [
                {'==': {VProps.VITRAGE_DATASOURCE_NAME: driver_name}},
                {'<': {VProps.VITRAGE_SAMPLE_TIMESTAMP: now}},
                {'==': {VProps.VITRAGE_IS_DELETED: False}},
            ]
        }

        return self.graph.get_vertices(query_dict=query)


class DriversNotificationEndpoint(object):

    def __init__(self, processor_func):
        self._processor_func = processor_func
        self._enrich_event_methods = defaultdict(list)

    def init(self):
        driver_names = utils.get_push_drivers_names()
        push_drivers = utils.get_drivers_by_name(driver_names)
        for driver in push_drivers:
            for event in driver.get_event_types():
                self._enrich_event_methods[event].append(driver.enrich_event)
        return self

    def get_listener(self):
        topics = CONF.datasources.notification_topics
        exchange = CONF.datasources.notification_exchange
        transport = messaging.get_transport()
        targets = [oslo_messaging.Target(exchange=exchange, topic=topic)
                   for topic in topics]

        return messaging.get_notification_listener(transport, targets, [self])

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        enrich_event_methods = self._enrich_event_methods[event_type]
        events = []
        for enrich_event_method in enrich_event_methods:
            result = enrich_event_method(payload, event_type)
            if isinstance(result, list):
                events += result
            else:
                events.append(result)
        events = [x for x in events if x is not None]
        LOG.info('EVENTS ENQUEUED:[%s] [%s] \n%s', publisher_id,
                 event_type, events)
        self._processor_func(events)


class LockByDriver(object):

    def __init__(self):
        self.lock_by_driver = dict()

    def acquire(self, driver_name, blocking=True):
        if not self.lock_by_driver.get(driver_name):
            self.lock_by_driver[driver_name] = threading.Lock()
        return self.lock_by_driver[driver_name].acquire(blocking)

    def release(self, driver_name):
        self.lock_by_driver[driver_name].release()


LOCK_BY_DRIVER = LockByDriver()
