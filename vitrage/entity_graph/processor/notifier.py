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
from oslo_config import cfg
from oslo_log import log
import oslo_messaging

from vitrage.common.constants import EdgeLabel as ELabel
from vitrage.common.constants import EdgeProperties as EProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import NotifierEventTypes
from vitrage.common.constants import VertexProperties as VProps
from vitrage.evaluator.actions import evaluator_event_transformer as evaluator
from vitrage.graph.driver.networkx_graph import edge_copy
from vitrage.graph.driver.networkx_graph import vertex_copy
from vitrage.messaging import get_transport

CONF = cfg.CONF

LOG = log.getLogger(__name__)


class GraphNotifier(object):
    """Allows writing to message bus"""
    def __init__(self):
        self.oslo_notifier = None
        topics = self._get_topics()
        if not topics:
            LOG.info('Graph Notifier is disabled')
            return
        self.oslo_notifier = oslo_messaging.Notifier(
            get_transport(),
            driver='messagingv2',
            publisher_id='vitrage.graph',
            topics=topics)

    @property
    def enabled(self):
        return self.oslo_notifier is not None

    def _get_topics(self):
        topics = []

        try:
            notifier_topic = CONF.entity_graph.notifier_topic
            notifier_plugins = CONF.notifiers
            if notifier_topic and notifier_plugins:
                topics.append(notifier_topic)
        except Exception:
            LOG.exception('Graph Notifier - missing configuration')

        try:
            machine_learning_topic = \
                CONF.machine_learning.machine_learning_topic
            machine_learning_plugins = CONF.machine_learning.plugins
            if machine_learning_topic and machine_learning_plugins:
                topics.append(machine_learning_topic)
        except Exception:
            LOG.info('Machine Learning - missing configuration')

        return topics

    def notify_when_applicable(self, before, current, is_vertex, graph):
        curr = current
        notification_types = \
            self._get_notification_type(before, curr, is_vertex)
        if not notification_types:
            return

        # in case the vertex point to some resource add the resource to the
        # notification (useful for deduce alarm notifications)
        if curr.get(VProps.VITRAGE_RESOURCE_ID):
            curr = vertex_copy(curr.vertex_id, curr.properties)
            curr.properties[VProps.RESOURCE] = graph.get_vertex(
                curr.get(VProps.VITRAGE_RESOURCE_ID))

        LOG.debug('notification_types : %s', notification_types)
        LOG.debug('notification properties : %s', curr.properties)

        for notification_type in notification_types:
            try:
                self.oslo_notifier.info(
                    {},
                    notification_type,
                    curr.properties)
            except Exception:
                LOG.exception('Cannot notify - %s.', notification_type)

    @staticmethod
    def _get_notification_type(before, current, is_vertex):
        if not is_vertex:
            return None

        notification_types = [
            notification_type(
                before, current, _is_active_deduced_alarm,
                NotifierEventTypes.ACTIVATE_DEDUCED_ALARM_EVENT,
                NotifierEventTypes.DEACTIVATE_DEDUCED_ALARM_EVENT),
            notification_type(
                before, current, _is_active_alarm,
                NotifierEventTypes.ACTIVATE_ALARM_EVENT,
                NotifierEventTypes.DEACTIVATE_ALARM_EVENT),
            notification_type(
                before, current, _is_marked_down,
                NotifierEventTypes.ACTIVATE_MARK_DOWN_EVENT,
                NotifierEventTypes.DEACTIVATE_MARK_DOWN_EVENT),
        ]
        return list(filter(None, notification_types))


class PersistNotifier(object):
    """Allows writing to message bus"""
    def __init__(self):
        self.oslo_notifier = None
        topics = [CONF.persistency.persistor_topic]
        self.oslo_notifier = oslo_messaging.Notifier(
            get_transport(),
            driver='messagingv2',
            publisher_id='vitrage.graph',
            topics=topics)

    def notify_when_applicable(self, before, current, is_vertex, graph):

        curr = current
        notification_types = \
            self._get_notification_type(before, curr, is_vertex)
        if not notification_types:
            return

        # in case the event is on edge, add source and target ids to properties
        # for history
        if not is_vertex:
            curr = edge_copy(
                curr.source_id, curr.target_id, curr.label, curr.properties)
            curr.properties[EProps.SOURCE_ID] = curr.source_id
            curr.properties[EProps.TARGET_ID] = curr.target_id

        LOG.debug('persist_notification_types : %s', notification_types)
        LOG.debug('persist_notification properties : %s', curr.properties)

        for notification_type in notification_types:
            try:
                self.oslo_notifier.info(
                    {},
                    notification_type,
                    curr.properties)
            except Exception:
                LOG.exception('Cannot notify - %s.', notification_type)

    @staticmethod
    def _get_notification_type(before, current, is_vertex):

        notification_types = [
            notification_type(
                before, current, _is_active_alarm,
                NotifierEventTypes.ACTIVATE_ALARM_EVENT,
                NotifierEventTypes.DEACTIVATE_ALARM_EVENT),
            notification_type(
                before, current, _is_active_causes_edge,
                NotifierEventTypes.ACTIVATE_CAUSAL_RELATION,
                NotifierEventTypes.DEACTIVATE_CAUSAL_RELATION),
            NotifierEventTypes.CHANGE_IN_ALARM_EVENT if
            _is_alarm_severity_change(before, current) else None,
            NotifierEventTypes.CHANGE_PROJECT_ID_EVENT if
            _is_resource_project_id_change(before, current) else None,
        ]
        return list(filter(None, notification_types))


def notification_type(before,
                      current,
                      is_active,
                      activate_event_type,
                      deactivate_event_type):
    if not is_active(before):
        if is_active(current):
            return activate_event_type
    else:
        if not is_active(current):
            return deactivate_event_type


def _is_active_deduced_alarm(entity):
    if not entity:
        return False
    if entity.get(VProps.VITRAGE_CATEGORY) == EntityCategory.ALARM and \
            entity.get(VProps.VITRAGE_TYPE) == evaluator.VITRAGE_DATASOURCE:
        return _is_relevant_vertex(entity)
    return False


def _is_active_alarm(entity):
    if entity and entity.get(VProps.VITRAGE_CATEGORY) == EntityCategory.ALARM:
        return _is_relevant_vertex(entity)
    return False


def _is_marked_down(entity):
    if not entity:
        return False
    if entity.get(VProps.VITRAGE_CATEGORY) == EntityCategory.RESOURCE and \
            entity.get(VProps.IS_MARKED_DOWN) is True:
        return _is_relevant_vertex(entity)
    return False


def _is_relevant_vertex(entity):
    if entity.get(VProps.VITRAGE_IS_DELETED, False) or \
            entity.get(VProps.VITRAGE_IS_PLACEHOLDER, False):
        return False
    return True


def _is_active_causes_edge(entity):
    if not entity:
        return False
    if not entity.get(EProps.RELATIONSHIP_TYPE) == ELabel.CAUSES:
        return False
    return not entity.get(EProps.VITRAGE_IS_DELETED)


def _is_alarm_severity_change(before, curr):
    if not (_is_active_alarm(before) and
            _is_active_alarm(curr)):
        return False
    # returns true on activation, deactivation and severity change
    if not before and curr \
            or (before.get(VProps.VITRAGE_OPERATIONAL_SEVERITY) !=
                curr.get(VProps.VITRAGE_OPERATIONAL_SEVERITY)):
        return True
    return False


def _is_resource_project_id_change(before, curr):
    if not (_is_active_alarm(before) and
            _is_active_alarm(curr)):
        return False
    if (before.get(VProps.VITRAGE_RESOURCE_PROJECT_ID) !=
            curr.get(VProps.VITRAGE_RESOURCE_PROJECT_ID)):
        return True
    return False
