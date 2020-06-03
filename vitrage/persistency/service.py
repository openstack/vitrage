# Copyright 2017 - Nokia
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

from datetime import timedelta

from concurrent.futures import ThreadPoolExecutor
import dateutil.parser
from futurist import periodics

from oslo_config import cfg
from oslo_log import log
import oslo_messaging as oslo_m
from oslo_utils import timeutils

from vitrage.common.constants import EdgeProperties as EProps
from vitrage.common.constants import ElementProperties as ElementProps
from vitrage.common.constants import HistoryProps as HProps
from vitrage.common.constants import NotifierEventTypes as NETypes
from vitrage.common.constants import VertexProperties as VProps
from vitrage.common.utils import spawn
from vitrage.coordination import service as coord
from vitrage import messaging
from vitrage.storage.sqlalchemy import models
from vitrage.utils.datetime import utcnow

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class PersistorService(coord.Service):
    def __init__(self, worker_id, db_connection):
        super(PersistorService, self).__init__(worker_id)
        self.db_connection = db_connection
        transport = messaging.get_transport()
        target = \
            oslo_m.Target(topic=CONF.persistency.persistor_topic)
        self.listener = messaging.get_notification_listener(
            transport, [target],
            [VitragePersistorEndpoint(self.db_connection)])
        self.scheduler = Scheduler(db_connection)

    def run(self):
        super(PersistorService, self).run()
        LOG.info("Vitrage Persistor Service - Starting...")

        self.listener.start()
        self.scheduler.start_periodic_tasks()

        LOG.info("Vitrage Persistor Service - Started!")

    def terminate(self):
        super(PersistorService, self).terminate()
        LOG.info("Vitrage Persistor Service - Stopping...")

        self.listener.stop()
        self.listener.wait()

        LOG.info("Vitrage Persistor Service - Stopped!")


class VitragePersistorEndpoint(object):
    def __init__(self, db_connection):
        self.db = db_connection
        self.event_type_to_writer = {
            NETypes.ACTIVATE_ALARM_EVENT: self._persist_activated_alarm,
            NETypes.DEACTIVATE_ALARM_EVENT: self._persist_deactivate_alarm,
            NETypes.ACTIVATE_CAUSAL_RELATION: self._persist_activate_edge,
            NETypes.DEACTIVATE_CAUSAL_RELATION: self._persist_deactivate_edge,
            NETypes.CHANGE_IN_ALARM_EVENT: self._persist_change,
            NETypes.CHANGE_PROJECT_ID_EVENT: self._persist_alarm_proj_change,
        }

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        LOG.debug('Event_type: %s Payload %s', event_type, payload)
        self.process_event(event_type, payload)

    def process_event(self, event_type, payload):
        writer = self.event_type_to_writer.get(event_type)
        if not writer:
            LOG.warning('Unrecognized event_type: %s', event_type)
            return
        writer(event_type, payload)

    def _persist_activated_alarm(self, event_type, data):
        event_timestamp = self.event_time(data)

        alarm_row = \
            models.Alarm(
                vitrage_id=data.get(VProps.VITRAGE_ID),
                start_timestamp=event_timestamp,
                name=data.get(VProps.NAME),
                vitrage_type=data.get(VProps.VITRAGE_TYPE),
                vitrage_aggregated_severity=data.get(
                    VProps.VITRAGE_AGGREGATED_SEVERITY),
                vitrage_operational_severity=data.get(
                    VProps.VITRAGE_OPERATIONAL_SEVERITY),
                project_id=data.get(VProps.PROJECT_ID),
                vitrage_resource_type=data.get(VProps.VITRAGE_RESOURCE_TYPE),
                vitrage_resource_id=data.get(VProps.VITRAGE_RESOURCE_ID),
                vitrage_resource_project_id=data.get(
                    VProps.VITRAGE_RESOURCE_PROJECT_ID),
                payload=data)
        self.db.alarms.create(alarm_row)

    def _persist_deactivate_alarm(self, event_type, data):
        vitrage_id = data.get(VProps.VITRAGE_ID)
        event_timestamp = self.event_time(data)
        self.db.alarms.update(
            vitrage_id, HProps.END_TIMESTAMP, event_timestamp)

    def _persist_alarm_proj_change(self, event_type, data):
        vitrage_id = data.get(VProps.VITRAGE_ID)
        self.db.alarms.update(vitrage_id,
                              VProps.VITRAGE_RESOURCE_PROJECT_ID,
                              data.get(VProps.VITRAGE_RESOURCE_PROJECT_ID))

    def _persist_activate_edge(self, event_type, data):
        event_timestamp = self.event_time(data)

        edge_row = \
            models.Edge(
                source_id=data.get(EProps.SOURCE_ID),
                target_id=data.get(EProps.TARGET_ID),
                label=data.get(EProps.RELATIONSHIP_TYPE),
                start_timestamp=event_timestamp,
                payload=data)
        self.db.edges.create(edge_row)

    def _persist_deactivate_edge(self, event_type, data):
        event_timestamp = self.event_time(data)
        source_id = data.get(EProps.SOURCE_ID)
        target_id = data.get(EProps.TARGET_ID)
        self.db.edges.update(
            source_id, target_id, end_timestamp=event_timestamp)

    def _persist_change(self, event_type, data):
        event_timestamp = self.event_time(data)
        change_row = \
            models.Change(
                vitrage_id=data.get(VProps.VITRAGE_ID),
                timestamp=event_timestamp,
                severity=data.get(VProps.VITRAGE_OPERATIONAL_SEVERITY),
                payload=data)
        self.db.changes.create(change_row)

    @staticmethod
    def event_time(data):
        event_timestamp = \
            dateutil.parser.parse(data.get(ElementProps.UPDATE_TIMESTAMP))
        event_timestamp = timeutils.normalize_time(event_timestamp)
        return event_timestamp


class Scheduler(object):

    def __init__(self, db):
        self.db = db
        self.periodic = None

    def start_periodic_tasks(self):
        self.periodic = periodics.PeriodicWorker.create(
            [], executor_factory=lambda: ThreadPoolExecutor(max_workers=10))

        self.add_events_table_expirer_timer()
        self.add_history_tables_expirer_timer()
        spawn(self.periodic.start)

    def add_events_table_expirer_timer(self):
        spacing = 60

        @periodics.periodic(spacing=spacing)
        def expirer_periodic():
            try:
                event_id = self.db.graph_snapshots.query_snapshot_event_id()
                if event_id:
                    LOG.debug('Table events - deleting event id=%s', event_id)
                    self.db.events.delete(event_id)

            except Exception:
                LOG.exception('Table events - periodic cleanup run failed.')

        self.periodic.add(expirer_periodic)
        LOG.info("Table events - periodic cleanup started (%ss)", spacing)

    def add_history_tables_expirer_timer(self):
        spacing = 60

        @periodics.periodic(spacing=spacing)
        def expirer_periodic():
            expire_by = \
                utcnow(with_timezone=False) - \
                timedelta(days=CONF.persistency.alarm_history_ttl)
            try:
                self.db.alarms.delete_expired(expire_by)
            except Exception:
                LOG.exception('History tables - periodic cleanup run failed.')

        self.periodic.add(expirer_periodic)
        LOG.info("History tables - periodic cleanup started (%ss)", spacing)
