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

import functools
import logging
import threading

from oslo_config import cfg
from oslo_db import api as oslo_db_api
from oslo_db.sqlalchemy import enginefacade
from oslo_log import log
from sqlalchemy import and_, or_
from sqlalchemy.engine import url as sqlalchemy_url
from sqlalchemy import exc as sa_exc
from sqlalchemy import func
import tenacity

from vitrage.common.exception import VitrageInputError
from vitrage.entity_graph.mappings.operational_alarm_severity import \
    OperationalAlarmSeverity
from vitrage import storage
from vitrage.storage import base
from vitrage.storage.history_facade import HistoryFacadeConnection
from vitrage.storage.sqlalchemy import models
from vitrage.storage.sqlalchemy.models import Template

CONF = cfg.CONF
DB_CONFIGURED = False
LOG = log.getLogger(__name__)
_CONTEXT = threading.local()


def _session_for_read():
    session = enginefacade.reader.using(_CONTEXT)
    return session


def _session_for_write():
    session = enginefacade.writer.using(_CONTEXT)
    return session


def wrap_sqlite_retry(f):

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if ('sqlite' not in CONF.database.connection.lower()):
            return f(*args, **kwargs)
        else:
            for attempt in tenacity.Retrying(
                retry=(
                    tenacity.retry_if_exception_type(
                        sa_exc.OperationalError)
                    & tenacity.retry_if_exception(
                        lambda e: 'database is locked' in str(e))
                ),
                wait=tenacity.wait_random(
                    min=0.1,
                    max=1,
                ),
                before_sleep=(
                    tenacity.before_sleep_log(LOG, logging.DEBUG)
                ),
                stop=tenacity.stop_after_delay(max_delay=10),
                reraise=False
            ):
                with attempt:
                    return f(*args, **kwargs)
    return wrapper


class Connection(base.Connection):
    def __init__(self, url):
        global DB_CONFIGURED

        if not DB_CONFIGURED:
            options = dict(CONF.database.items())
            options['connection'] = self._dress_url(url)
            # set retries to 0 , since reconnection is already implemented
            # in storage.__init__.get_connection_from_config function
            options['max_retries'] = 0
            # add vitrage opts to database group
            for opt in storage.OPTS:
                options.pop(opt.name, None)

            enginefacade.configure(**options)

            DB_CONFIGURED = True

        self._active_actions = ActiveActionsConnection()
        self._events = EventsConnection()
        self._templates = TemplatesConnection()
        self._graph_snapshots = GraphSnapshotsConnection()
        self._webhooks = WebhooksConnection()
        self._alarms = AlarmsConnection()
        self._edges = EdgesConnection()
        self._changes = ChangesConnection()
        self._history_facade = HistoryFacadeConnection(
            self._alarms, self._edges, self._changes)

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

    def clear(self):
        engine = enginefacade.writer.get_engine()
        for table in reversed(models.Base.metadata.sorted_tables):
            engine.execute(table.delete())
        engine.dispose()


class BaseTableConn(object):
    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def bulk_create(self, items):
        if not items:
            return

        with _session_for_write() as session:
            session.bulk_save_objects(items)

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def query_filter(self, model, action, **kwargs):
        with _session_for_write() as session:
            query = session.query(model)
            for keyword, arg in kwargs.items():
                if arg is not None:
                    query = query.filter(getattr(model, keyword) == arg)
            query = getattr(query, action)()
        return query


class TemplatesConnection(base.TemplatesConnection, BaseTableConn):
    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def create(self, template):
        with _session_for_write() as session:
            session.add(template)

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def update(self, uuid, var, value):
        with _session_for_write() as session:
            session.query(Template).filter_by(uuid=uuid).update({var: value})

    def query(self, name=None, file_content=None,
              uuid=None, status=None, status_details=None,
              template_type=None):
        query = self.query_filter(
            models.Template,
            'all',
            name=name,
            file_content=file_content,
            uuid=uuid,
            status=status,
            status_details=status_details,
            template_type=template_type,
            )
        return query

    @wrap_sqlite_retry
    def query_with_status_not(self, name, status):
        with _session_for_read() as session:
            query = session.query(models.Template)
            query = query.filter(
                and_
                (
                    models.Template.status != status,
                    models.Template.name == name
                )
            )
            result = query.first()
        return result

    def delete(self, name=None, uuid=None):
        query = self.query_filter(
            models.Template,
            'delete',
            name=name,
            uuid=uuid,
            )
        return query


class ActiveActionsConnection(base.ActiveActionsConnection, BaseTableConn):
    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def create(self, active_action):
        with _session_for_write() as session:
            session.add(active_action)

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def update(self, active_action):
        with _session_for_write() as session:
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
            'all',
            action_type=action_type,
            extra_info=extra_info,
            source_vertex_id=source_vertex_id,
            target_vertex_id=target_vertex_id,
            action_id=action_id,
            score=score,
            trigger=trigger)
        return query

    @wrap_sqlite_retry
    def query_similar(self, actions):
        """Query DB for all actions with same properties"""
        with _session_for_read() as session:
            query = session.query(models.ActiveAction)

            filters = []
            for source, target, extra_info, action_type in actions:
                filters.append(
                    and_(models.ActiveAction.action_type == action_type,
                         models.ActiveAction.extra_info == extra_info,
                         models.ActiveAction.source_vertex_id == source,
                         models.ActiveAction.target_vertex_id == target,))
            query = query.filter(or_(*filters))
            result = query.all()
        return result

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
            'delete',
            action_type=action_type,
            extra_info=extra_info,
            source_vertex_id=source_vertex_id,
            target_vertex_id=target_vertex_id,
            action_id=action_id,
            score=score,
            trigger=trigger)
        return query

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def bulk_delete(self, actions):
        if not actions:
            return
        with _session_for_write() as session:
            query = session.query(models.ActiveAction)

            filters = []
            for trigger, action_id in actions:
                filters.append(
                    and_(models.ActiveAction.trigger == trigger,
                         models.ActiveAction.action_id == action_id))
            query = query.filter(or_(*filters))
            result = query.delete()
        return result


class WebhooksConnection(base.WebhooksConnection,
                         BaseTableConn):
    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def create(self, webhook):
        with _session_for_write() as session:
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
            'all',
            id=id,
            project_id=project_id,
            is_admin_webhook=is_admin_webhook,
            url=url,
            headers=headers,
            regex_filter=regex_filter)
        return query

    def delete(self, id=None):
        query = self.query_filter(models.Webhooks, 'delete', id=id)
        return query


class EventsConnection(base.EventsConnection, BaseTableConn):
    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def create(self, event):
        with _session_for_write() as session:
            session.add(event)

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def update(self, event):
        with _session_for_write() as session:
            session.merge(event)

    @wrap_sqlite_retry
    def get_last_event_id(self):
        with _session_for_read() as session:
            query = session.query(models.Event.event_id)
            result = query.order_by(models.Event.event_id.desc()).first()
        return result

    @wrap_sqlite_retry
    def get_replay_events(self, event_id):
        """Get all events that occurred after the specified event_id

        :rtype: list of vitrage.storage.sqlalchemy.models.Event
        """
        with _session_for_read() as session:
            query = session.query(models.Event)
            query = query.filter(models.Event.event_id > event_id)
            result = query.order_by(models.Event.event_id.asc()).all()
        return result

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

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def delete(self, event_id=None):
        """Delete all events older than event_id"""
        with _session_for_write() as session:
            query = session.query(models.Event)
            if event_id:
                query = query.filter(models.Event.event_id < event_id)
            query.delete()


class GraphSnapshotsConnection(base.GraphSnapshotsConnection, BaseTableConn):
    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def create(self, graph_snapshot):
        with _session_for_write() as session:
            session.add(graph_snapshot)

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def update(self, graph_snapshot):
        with _session_for_write() as session:
            session.merge(graph_snapshot)

    @wrap_sqlite_retry
    def query(self):
        with _session_for_read() as session:
            query = session.query(models.GraphSnapshot)
            result = query.first()
        return result

    @wrap_sqlite_retry
    def query_snapshot_event_id(self):
        """Select the event_id of the stored snapshot"""
        with _session_for_read() as session:
            query = session.query(models.GraphSnapshot.event_id)
            result = query.first()
        return result[0] if result else None

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def delete(self):
        """Delete all graph snapshots"""
        with _session_for_write() as session:
            query = session.query(models.GraphSnapshot)
            query.delete()


class AlarmsConnection(base.AlarmsConnection, BaseTableConn):
    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def create(self, alarm):
        with _session_for_write() as session:
            session.add(alarm)

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def update(self, vitrage_id, key, val):
        with _session_for_write() as session:
            query = session.query(models.Alarm).filter(
                models.Alarm.vitrage_id == vitrage_id)
            query.update({getattr(models.Alarm, key): val})

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def end_all_alarms(self, end_time):
        with _session_for_write() as session:
            query = session.query(models.Alarm).filter(
                models.Alarm.end_timestamp > end_time)
            query.update({models.Alarm.end_timestamp: end_time})

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def delete_expired(self, expire_by=None):
        with _session_for_write() as session:
            query = session.query(models.Alarm)
            query = query.filter(models.Alarm.end_timestamp < expire_by)
            del_query = query.delete()
        return del_query

    def delete(self,
               vitrage_id=None,
               start_timestamp=None,
               end_timestamp=None):
        query = self.query_filter(
            models.Alarm,
            'delete',
            vitrage_id=vitrage_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp)
        return query


class EdgesConnection(base.EdgesConnection, BaseTableConn):
    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def create(self, edge):
        with _session_for_write() as session:
            session.add(edge)

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def update(self, source_id, target_id, end_timestamp):
        with _session_for_write() as session:
            query = session.query(models.Edge).filter(and_(
                models.Edge.source_id == source_id,
                models.Edge.target_id == target_id))
            query.update({models.Edge.end_timestamp: end_timestamp})

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def end_all_edges(self, end_time):
        with _session_for_write() as session:
            query = session.query(models.Edge).filter(
                models.Edge.end_timestamp > end_time)
            query.update({models.Edge.end_timestamp: end_time})

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def delete(self):
        with _session_for_write() as session:
            query = session.query(models.Edge)
            result = query.delete()
        return result


class ChangesConnection(base.ChangesConnection, BaseTableConn):
    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def create(self, change):
        with _session_for_write() as session:
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

    @wrap_sqlite_retry
    def _get_alarms_last_change(self, alarm_ids):
        with _session_for_read() as session:
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

    @wrap_sqlite_retry
    @oslo_db_api.retry_on_deadlock
    def delete(self):
        with _session_for_write() as session:
            query = session.query(models.Change)
            result = query.delete()
        return result
