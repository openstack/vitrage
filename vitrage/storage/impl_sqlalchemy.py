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

from oslo_config import cfg
from oslo_db.sqlalchemy import session as db_session
from oslo_log import log
from sqlalchemy import and_, or_
from sqlalchemy.engine import url as sqlalchemy_url
from sqlalchemy import func

from vitrage.common.exception import VitrageInputError
from vitrage.entity_graph.mappings.operational_alarm_severity import \
    OperationalAlarmSeverity
from vitrage import storage
from vitrage.storage import base
from vitrage.storage.history_facade import HistoryFacadeConnection
from vitrage.storage.sqlalchemy import models
from vitrage.storage.sqlalchemy.models import Template

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Connection(base.Connection):
    def __init__(self, url):
        options = dict(CONF.database.items())
        # set retries to 0 , since reconnection is already implemented
        # in storage.__init__.get_connection_from_config function
        options['max_retries'] = 0
        # add vitrage opts to database group
        for opt in storage.OPTS:
            options.pop(opt.name, None)
        self._engine_facade = db_session.EngineFacade(self._dress_url(url),
                                                      **options)
        self._active_actions = ActiveActionsConnection(self._engine_facade)
        self._events = EventsConnection(self._engine_facade)
        self._templates = TemplatesConnection(self._engine_facade)
        self._graph_snapshots = GraphSnapshotsConnection(self._engine_facade)
        self._webhooks = WebhooksConnection(
            self._engine_facade)
        self._alarms = AlarmsConnection(
            self._engine_facade)
        self._edges = EdgesConnection(
            self._engine_facade)
        self._changes = ChangesConnection(
            self._engine_facade)
        self._history_facade = HistoryFacadeConnection(
            self._engine_facade, self._alarms, self._edges, self._changes)

    @property
    def webhooks(self):
        return self._webhooks

    @property
    def active_actions(self):
        return self._active_actions

    @property
    def events(self):
        return self._events

    @property
    def templates(self):
        return self._templates

    @property
    def graph_snapshots(self):
        return self._graph_snapshots

    @property
    def alarms(self):
        return self._alarms

    @property
    def edges(self):
        return self._edges

    @property
    def changes(self):
        return self._changes

    @property
    def history_facade(self):
        return self._history_facade

    @staticmethod
    def _dress_url(url):
        # If no explicit driver has been set, we default to pymysql
        if url.startswith("mysql://"):
            url = sqlalchemy_url.make_url(url)
            url.drivername = "mysql+pymysql"
            return str(url)
        return url

    def disconnect(self):
        self._engine_facade.get_engine().dispose()

    def clear(self):
        engine = self._engine_facade.get_engine()
        for table in reversed(models.Base.metadata.sorted_tables):
            engine.execute(table.delete())
        engine.dispose()


class BaseTableConn(object):
    def __init__(self, engine_facade):
        super(BaseTableConn, self).__init__()
        self._engine_facade = engine_facade

    def bulk_create(self, items):
        if not items:
            return

        session = self._engine_facade.get_session()
        with session.begin():
            session.bulk_save_objects(items)

    def query_filter(self, model, **kwargs):
        session = self._engine_facade.get_session()
        query = session.query(model)
        for keyword, arg in kwargs.items():
            if arg is not None:
                query = query.filter(getattr(model, keyword) == arg)
        return query


class TemplatesConnection(base.TemplatesConnection, BaseTableConn):
    def __init__(self, engine_facade):
        super(TemplatesConnection, self).__init__(engine_facade)

    def create(self, template):
        session = self._engine_facade.get_session()
        with session.begin():
            session.add(template)

    def update(self, uuid, var, value):
        session = self._engine_facade.get_session()
        with session.begin():
            session.query(Template).filter_by(uuid=uuid).update({var: value})

    def query(self, name=None, file_content=None,
              uuid=None, status=None, status_details=None,
              template_type=None):
        query = self.query_filter(
            models.Template,
            name=name,
            file_content=file_content,
            uuid=uuid,
            status=status,
            status_details=status_details,
            template_type=template_type,
            )
        return query.all()

    def query_with_status_not(self, name, status):
        session = self._engine_facade.get_session()
        query = session.query(models.Template)
        query = query.filter(
            and_
            (
                models.Template.status != status,
                models.Template.name == name
            )
        )
        return query.first()

    def delete(self, name=None, uuid=None):
        query = self.query_filter(
            models.Template,
            name=name,
            uuid=uuid,
            )
        return query.delete()


class ActiveActionsConnection(base.ActiveActionsConnection, BaseTableConn):
    def __init__(self, engine_facade):
        super(ActiveActionsConnection, self).__init__(engine_facade)

    def create(self, active_action):
        session = self._engine_facade.get_session()
        with session.begin():
            session.add(active_action)

    def update(self, active_action):
        session = self._engine_facade.get_session()
        with session.begin():
            session.merge(active_action)

    def query(self,
              action_type=None,
              extra_info=None,
              source_vertex_id=None,
              target_vertex_id=None,
              action_id=None,
              score=None,
              trigger=None):
        query = self.query_filter(
            models.ActiveAction,
            action_type=action_type,
            extra_info=extra_info,
            source_vertex_id=source_vertex_id,
            target_vertex_id=target_vertex_id,
            action_id=action_id,
            score=score,
            trigger=trigger)
        return query.all()

    def query_similar(self, actions):
        """Query DB for all actions with same properties"""
        session = self._engine_facade.get_session()
        query = session.query(models.ActiveAction)

        filters = []
        for source, target, extra_info, action_type in actions:
            filters.append(
                and_(models.ActiveAction.action_type == action_type,
                     models.ActiveAction.extra_info == extra_info,
                     models.ActiveAction.source_vertex_id == source,
                     models.ActiveAction.target_vertex_id == target,))
        query = query.filter(or_(*filters))
        return query.all()

    def delete(self,
               action_type=None,
               extra_info=None,
               source_vertex_id=None,
               target_vertex_id=None,
               action_id=None,
               score=None,
               trigger=None):
        query = self.query_filter(
            models.ActiveAction,
            action_type=action_type,
            extra_info=extra_info,
            source_vertex_id=source_vertex_id,
            target_vertex_id=target_vertex_id,
            action_id=action_id,
            score=score,
            trigger=trigger)
        return query.delete()

    def bulk_delete(self, actions):
        if not actions:
            return
        session = self._engine_facade.get_session()
        query = session.query(models.ActiveAction)

        filters = []
        for trigger, action_id in actions:
            filters.append(
                and_(models.ActiveAction.trigger == trigger,
                     models.ActiveAction.action_id == action_id))
        query = query.filter(or_(*filters))
        return query.delete()


class WebhooksConnection(base.WebhooksConnection,
                         BaseTableConn):
    def __init__(self, engine_facade):
        super(WebhooksConnection, self).__init__(engine_facade)

    def create(self, webhook):
        session = self._engine_facade.get_session()
        with session.begin():
            session.add(webhook)

    def query(self,
              id=None,
              project_id=None,
              is_admin_webhook=None,
              url=None,
              headers=None,
              regex_filter=None):
        query = self.query_filter(
            models.Webhooks,
            id=id,
            project_id=project_id,
            is_admin_webhook=is_admin_webhook,
            url=url,
            headers=headers,
            regex_filter=regex_filter)
        return query.all()

    def delete(self, id=None):
        query = self.query_filter(models.Webhooks, id=id)
        return query.delete()


class EventsConnection(base.EventsConnection, BaseTableConn):
    def __init__(self, engine_facade):
        super(EventsConnection, self).__init__(engine_facade)

    def create(self, event):
        session = self._engine_facade.get_session()
        with session.begin():
            session.add(event)

    def update(self, event):
        session = self._engine_facade.get_session()
        with session.begin():
            session.merge(event)

    def get_last_event_id(self):
        session = self._engine_facade.get_session()
        query = session.query(models.Event.event_id)
        return query.order_by(models.Event.event_id.desc()).first()

    def get_replay_events(self, event_id):
        """Get all events that occurred after the specified event_id

        :rtype: list of vitrage.storage.sqlalchemy.models.Event
        """
        session = self._engine_facade.get_session()
        query = session.query(models.Event)
        query = query.filter(models.Event.event_id > event_id)
        return query.order_by(models.Event.event_id.asc()).all()

    def query(self,
              event_id=None,
              collector_timestamp=None,
              payload=None,
              gt_collector_timestamp=None,
              lt_collector_timestamp=None):
        """Yields a lists of events that match filters.

        :raises: vitrage.common.exception.VitrageInputError.
        :rtype: list of vitrage.storage.sqlalchemy.models.Event
        """

        if (event_id or collector_timestamp or payload) and \
           (gt_collector_timestamp or lt_collector_timestamp):
            msg = "Calling function with both specific event and range of " \
                  "events parameters at the same time "
            LOG.debug(msg)
            raise VitrageInputError(msg)

        query = self.query_filter(
            models.Event,
            event_id=event_id,
            collector_timestamp=collector_timestamp,
            payload=payload)

        query = self._update_query_gt_lt(gt_collector_timestamp,
                                         lt_collector_timestamp,
                                         query)

        return query.order_by(models.Event.collector_timestamp.desc()).all()

    @staticmethod
    def _update_query_gt_lt(gt_collector_timestamp,
                            lt_collector_timestamp,
                            query):
        if gt_collector_timestamp is not None:
            query = query.filter(models.Event.collector_timestamp >=
                                 gt_collector_timestamp)
        if lt_collector_timestamp is not None:
            query = query.filter(models.Event.collector_timestamp <=
                                 lt_collector_timestamp)
        return query

    def delete(self, event_id=None):
        """Delete all events older than event_id"""
        session = self._engine_facade.get_session()
        query = session.query(models.Event)
        if event_id:
            query = query.filter(models.Event.event_id < event_id)
        query.delete()


class GraphSnapshotsConnection(base.GraphSnapshotsConnection, BaseTableConn):
    def __init__(self, engine_facade):
        super(GraphSnapshotsConnection, self).__init__(engine_facade)

    def create(self, graph_snapshot):
        session = self._engine_facade.get_session()
        with session.begin():
            session.add(graph_snapshot)

    def update(self, graph_snapshot):
        session = self._engine_facade.get_session()
        with session.begin():
            session.merge(graph_snapshot)

    def query(self):
        query = self.query_filter(models.GraphSnapshot)
        return query.first()

    def query_snapshot_event_id(self):
        """Select the event_id of the stored snapshot"""
        session = self._engine_facade.get_session()
        query = session.query(models.GraphSnapshot.event_id)
        result = query.first()
        return result[0] if result else None

    def delete(self):
        """Delete all graph snapshots"""
        query = self.query_filter(models.GraphSnapshot)
        query.delete()


class AlarmsConnection(base.AlarmsConnection, BaseTableConn):
    def __init__(self, engine_facade):
        super(AlarmsConnection, self).__init__(engine_facade)

    def create(self, alarm):
        session = self._engine_facade.get_session()
        with session.begin():
            session.add(alarm)

    def update(self, vitrage_id, key, val):
        session = self._engine_facade.get_session()
        with session.begin():
            query = session.query(models.Alarm).filter(
                models.Alarm.vitrage_id == vitrage_id)
            query.update({getattr(models.Alarm, key): val})

    def end_all_alarms(self, end_time):
        session = self._engine_facade.get_session()
        query = session.query(models.Alarm).filter(
            models.Alarm.end_timestamp > end_time)
        query.update({models.Alarm.end_timestamp: end_time})

    def delete_expired(self, expire_by=None):
        session = self._engine_facade.get_session()
        query = session.query(models.Alarm)
        query = query.filter(models.Alarm.end_timestamp < expire_by)
        return query.delete()

    def delete(self,
               vitrage_id=None,
               start_timestamp=None,
               end_timestamp=None):
        query = self.query_filter(
            models.Alarm,
            vitrage_id=vitrage_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp)
        return query.delete()


class EdgesConnection(base.EdgesConnection, BaseTableConn):
    def __init__(self, engine_facade):
        super(EdgesConnection, self).__init__(engine_facade)

    def create(self, edge):
        session = self._engine_facade.get_session()
        with session.begin():
            session.add(edge)

    def update(self, source_id, target_id, end_timestamp):
        session = self._engine_facade.get_session()
        with session.begin():
            query = session.query(models.Edge).filter(and_(
                models.Edge.source_id == source_id,
                models.Edge.target_id == target_id))
            query.update({models.Edge.end_timestamp: end_timestamp})

    def end_all_edges(self, end_time):
        session = self._engine_facade.get_session()
        query = session.query(models.Edge).filter(
            models.Edge.end_timestamp > end_time)
        query.update({models.Edge.end_timestamp: end_time})

    def delete(self):
        query = self.query_filter(models.Edge)
        return query.delete()


class ChangesConnection(base.ChangesConnection, BaseTableConn):
    def __init__(self, engine_facade):
        super(ChangesConnection, self).__init__(engine_facade)

    def create(self, change):
        session = self._engine_facade.get_session()
        with session.begin():
            session.add(change)

    def add_end_changes(self, vitrage_ids, end_time):
        last_changes = self._get_alarms_last_change(vitrage_ids)
        for id, change in last_changes.items():
            change_row = \
                models.Change(
                    vitrage_id=id,
                    timestamp=end_time,
                    severity=OperationalAlarmSeverity.OK,
                    payload=change.payload)
            self.create(change_row)

    def _get_alarms_last_change(self, alarm_ids):
        session = self._engine_facade.get_session()
        query = session.query(func.max(models.Change.timestamp),
                              models.Change.vitrage_id,
                              models.Change.payload).\
            filter(models.Change.vitrage_id.in_(alarm_ids)).\
            group_by(models.Change.vitrage_id)

        rows = query.all()

        result = {}
        for change in rows:
            result[change.vitrage_id] = change

        return result

    def delete(self):
        query = self.query_filter(models.Change)
        return query.delete()
