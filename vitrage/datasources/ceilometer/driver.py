# Copyright 2016 - Alcatel-Lucent
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,  software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND,  either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_log import log

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.datasources.alarm_driver_base import AlarmDriverBase
from vitrage.datasources.ceilometer import CEILOMETER_DATASOURCE
from vitrage.datasources.ceilometer.properties \
    import CeilometerEventType as CeilEventType
from vitrage.datasources.ceilometer.properties \
    import CeilometerProperties as CeilProps
from vitrage.datasources.ceilometer.properties \
    import CeilometerState as CeilState
from vitrage import os_clients
from vitrage.utils import datetime as datetime_utils

LOG = log.getLogger(__name__)


class CeilometerDriver(AlarmDriverBase):

    def __init__(self):
        super(CeilometerDriver, self).__init__()
        self._client = None
        self._init_aodh_event_actions()
        self._cache_all_alarms()

    @property
    def client(self):
        if not self._client:
            self._client = os_clients.ceilometer_client()
        return self._client

    def _vitrage_type(self):
        return CEILOMETER_DATASOURCE

    def _alarm_key(self, alarm):
        return alarm[CeilProps.ALARM_ID]

    def _cache_all_alarms(self):
        alarms = self._get_alarms()
        self._filter_and_cache_alarms(alarms,
                                      self._filter_get_valid)

    def _get_alarms(self):
        try:
            aodh_alarms = self.client.alarms.list()
            return [self._convert_alarm(alarm) for alarm in
                    aodh_alarms if alarm is not None]
        except Exception:
            LOG.exception("Failed to get all alarms.")
        return []

    def _is_erroneous(self, alarm):
        return alarm and alarm[CeilProps.STATE] == CeilState.ALARM

    def _status_changed(self, alarm1, alarm2):
        return alarm1 and alarm2 and \
            not alarm1[CeilProps.STATE] == alarm2[CeilProps.STATE]

    def _is_valid(self, alarm):
        return True

    @classmethod
    def _convert_event_alarm(cls, alarm):
        res = cls._convert_base_alarm(alarm)
        res[CeilProps.EVENT_TYPE] = alarm.event_rule[CeilProps.EVENT_TYPE],
        res[CeilProps.RESOURCE_ID] = _parse_query(alarm.event_rule,
                                                  CeilProps.EVENT_RESOURCE_ID)
        return res

    @classmethod
    def _convert_threshold_alarm(cls, alarm):
        res = cls._convert_base_alarm(alarm)
        res[CeilProps.STATE_TIMESTAMP] = alarm.state_timestamp
        res[CeilProps.RESOURCE_ID] = _parse_query(alarm.threshold_rule,
                                                  CeilProps.RESOURCE_ID)
        return res

    @classmethod
    def _convert_gnocchi_resources_threshold(cls, alarm):
        res = cls._convert_base_alarm_gnocchi(alarm)
        if type(alarm) is not dict:
            alarm = alarm.to_dict()
            res[CeilProps.STATE_TIMESTAMP] = \
                alarm.get(CeilProps.STATE_TIMESTAMP)
            res[CeilProps.RESOURCE_ID] = \
                alarm.get(CeilProps.GNOCCHI_RESOURCES_THRESHOLD_RULE,
                          {}).get(CeilProps.RESOURCE_ID)
        else:
            res[CeilProps.STATE_TIMESTAMP] = \
                alarm.get(CeilProps.DETAIL, {}).get(CeilProps.STATE_TIMESTAMP)
            res[CeilProps.RESOURCE_ID] = \
                alarm.get(CeilProps.DETAIL,
                          {}).get(CeilProps.RULE,
                                  {}).get(CeilProps.RESOURCE_ID)
        return res

    @classmethod
    def _convert_vitrage_alarm(cls, alarm):
        res = cls._convert_base_alarm(alarm)
        res[CeilProps.VITRAGE_ID] = _parse_query(alarm.event_rule,
                                                 CeilProps.VITRAGE_ID)
        res[CeilProps.RESOURCE_ID] = _parse_query(alarm.event_rule,
                                                  CeilProps.RESOURCE_ID)
        return res

    @staticmethod
    def _convert_base_dict_alarm_gnocchi(alarm):
        detail = alarm.get(CeilProps.DETAIL)
        return {
            CeilProps.SEVERITY: alarm.get(CeilProps.SEVERITY),
            CeilProps.PROJECT_ID: alarm.get(CeilProps.PROJECT_ID),
            CeilProps.TIMESTAMP: alarm.get(CeilProps.TIMESTAMP),
            CeilProps.TYPE: alarm.get(CeilProps.TYPE),
            CeilProps.ALARM_ID: alarm.get(CeilProps.ALARM_ID),
            CeilProps.DESCRIPTION: detail.get(CeilProps.DESCRIPTION),
            CeilProps.ENABLED: detail.get(CeilProps.ENABLED),
            CeilProps.NAME: detail.get(CeilProps.NAME),
            CeilProps.REPEAT_ACTIONS: detail.get(CeilProps.REPEAT_ACTIONS),
            CeilProps.STATE: detail.get(CeilProps.STATE)
        }

    @staticmethod
    def _convert_base_non_dict_alarm_gnocchi(alarm):
        alarm = alarm.to_dict()
        return {
            CeilProps.SEVERITY: alarm.get(CeilProps.SEVERITY),
            CeilProps.DESCRIPTION: alarm.get(CeilProps.DESCRIPTION),
            CeilProps.ENABLED: alarm.get(CeilProps.ENABLED),
            CeilProps.ALARM_ID: alarm.get(CeilProps.ALARM_ID),
            CeilProps.NAME: alarm.get(CeilProps.NAME),
            CeilProps.PROJECT_ID: alarm.get(CeilProps.PROJECT_ID),
            CeilProps.REPEAT_ACTIONS: alarm.get(CeilProps.REPEAT_ACTIONS),
            CeilProps.STATE: alarm.get(CeilProps.STATE),
            CeilProps.TIMESTAMP: alarm.get(CeilProps.TIMESTAMP),
            CeilProps.TYPE: alarm.get(CeilProps.TYPE)
        }

    @classmethod
    def _convert_base_alarm_gnocchi(cls, alarm):
        """distinguish between alarm received by notification (type dict)

        to alarm received by _get_alarms() (type alarm).
        """

        if type(alarm) is dict:
            return cls._convert_base_dict_alarm_gnocchi(alarm)

        return cls._convert_base_non_dict_alarm_gnocchi(alarm)

    @staticmethod
    def _convert_base_alarm(alarm):
        return {
            CeilProps.SEVERITY: alarm.severity,
            CeilProps.DESCRIPTION: alarm.description,
            CeilProps.ENABLED: alarm.enabled,
            CeilProps.ALARM_ID: alarm.alarm_id,
            CeilProps.NAME: alarm.name,
            CeilProps.PROJECT_ID: alarm.project_id,
            CeilProps.REPEAT_ACTIONS: alarm.repeat_actions,
            CeilProps.STATE: alarm.state,
            CeilProps.TIMESTAMP: alarm.timestamp,
            CeilProps.TYPE: alarm.type
        }

    @classmethod
    def _convert_alarm(cls, alarm):
        alarm_type = alarm.type
        if alarm_type == CeilProps.EVENT and \
                _is_vitrage_alarm(alarm.event_rule):
            return cls._convert_vitrage_alarm(alarm)
        elif alarm_type == CeilProps.EVENT:
            return cls._convert_event_alarm(alarm)
        elif alarm_type == CeilProps.THRESHOLD:
            return cls._convert_threshold_alarm(alarm)
        elif alarm_type == CeilProps.GNOCCHI_RESOURCES_THRESHOLD:
            return cls._convert_gnocchi_resources_threshold(alarm)
        else:
            LOG.warning('Unsupported Ceilometer alarm type %s' % alarm_type)

    @staticmethod
    def get_event_types():
        # Add event_types to receive notifications about
        return [CeilEventType.CREATION,
                CeilEventType.STATE_TRANSITION,
                CeilEventType.RULE_CHANGE,
                CeilEventType.DELETION]

    def enrich_event(self, event, event_type):
        if event_type in self.actions:
            entity = self.actions[event_type](event)
        else:
            LOG.warning('Unsupported Ceilometer event type %s' % event_type)
            return None

        # Don't need to update entity, only update the cache
        if entity is None:
            return None

        entity[DSProps.EVENT_TYPE] = event_type

        return CeilometerDriver.make_pickleable(
            [entity], CEILOMETER_DATASOURCE,
            DatasourceAction.UPDATE)[0]

    def _init_aodh_event_actions(self):
        self.actions = {
            CeilEventType.CREATION:
                self._convert_alarm_creation_event,
            CeilEventType.RULE_CHANGE:
                self._convert_alarm_rule_change_event,
            CeilEventType.STATE_TRANSITION:
                self._convert_alarm_state_transition_event,
            CeilEventType.DELETION:
                self._convert_alarm_deletion_event
        }

    @classmethod
    def _convert_base_event(cls, event):
        return {
            CeilProps.PROJECT_ID: event[CeilProps.PROJECT_ID],
            CeilProps.ALARM_ID: event[CeilProps.ALARM_ID],
            CeilProps.SEVERITY: event[CeilProps.SEVERITY],
            CeilProps.TIMESTAMP: event[CeilProps.TIMESTAMP],
            CeilProps.USER_ID: event[CeilProps.USER_ID]
        }

    @classmethod
    def _convert_vitrage_alarm_rule(cls, rule):
        return {
            CeilProps.VITRAGE_ID: _parse_query(rule, CeilProps.VITRAGE_ID),
            CeilProps.RESOURCE_ID: _parse_query(rule, CeilProps.RESOURCE_ID)
        }

    @classmethod
    def _convert_threshold_alarm_rule(cls, rule):
        return {
            CeilProps.RESOURCE_ID: _parse_query(rule, CeilProps.RESOURCE_ID),
        }

    @classmethod
    def _convert_gnocchi_resources_threshold_alarm_rule(cls, rule):
        return {
            CeilProps.RESOURCE_ID: _parse_query(rule, CeilProps.RESOURCE_ID),
        }

    @classmethod
    def _convert_event_alarm_rule(cls, rule):
        return {
            CeilProps.EVENT_TYPE: rule[CeilProps.EVENT_TYPE],
            CeilProps.RESOURCE_ID:
                _parse_query(rule, CeilProps.EVENT_RESOURCE_ID)
        }

    @classmethod
    def _convert_detail_event(cls, event):
        alarm_info = event[CeilProps.DETAIL]
        alarm_rule = alarm_info[CeilProps.RULE]

        entity_detail = {
            CeilProps.DESCRIPTION: alarm_info[CeilProps.DESCRIPTION],
            CeilProps.ENABLED: alarm_info[CeilProps.ENABLED],
            CeilProps.NAME: alarm_info[CeilProps.NAME],
            CeilProps.STATE: alarm_info[CeilProps.STATE],
            CeilProps.REPEAT_ACTIONS: alarm_info[CeilProps.REPEAT_ACTIONS],
            CeilProps.TYPE: alarm_info[CeilProps.TYPE],
            CeilProps.STATE_TIMESTAMP: alarm_info[CeilProps.STATE_TIMESTAMP],
            CeilProps.STATE_REASON: alarm_info[CeilProps.STATE_REASON]
        }

        if _is_vitrage_alarm(alarm_rule):
            entity_detail.update(cls._convert_vitrage_alarm_rule(alarm_rule))
        elif entity_detail[CeilProps.TYPE] == CeilProps.EVENT:
            entity_detail.update(cls._convert_event_alarm_rule(alarm_rule))
        elif entity_detail[CeilProps.TYPE] == CeilProps.THRESHOLD:
            entity_detail.update(
                cls._convert_threshold_alarm_rule(alarm_rule))
        elif entity_detail[CeilProps.TYPE] == \
                CeilProps.GNOCCHI_RESOURCES_THRESHOLD:
            entity_detail.update(
                cls._convert_gnocchi_resources_threshold_alarm_rule(
                    alarm_rule))

        return entity_detail

    @classmethod
    def _parse_changed_rule(cls, change_rule):
        entity = {}
        if CeilProps.EVENT_TYPE in change_rule:
            entity[CeilProps.EVENT_TYPE] = change_rule[CeilProps.EVENT_TYPE]
        if 'query' in change_rule:
            event_resource_id = \
                _parse_query(change_rule, CeilProps.EVENT_RESOURCE_ID)
            resource_id = \
                _parse_query(change_rule, CeilProps.RESOURCE_ID)
            if event_resource_id or resource_id:
                entity[CeilProps.RESOURCE_ID] = event_resource_id if \
                    event_resource_id is not None else resource_id

        return entity

    @staticmethod
    def should_delete_outdated_entities():
        return True

    def _convert_alarm_creation_event(self, event):
        entity = self._convert_base_event(event)
        detail = self._convert_detail_event(event)
        entity.update(detail)

        return self._filter_and_cache_alarm(entity, None,
                                            self._filter_get_erroneous,
                                            datetime_utils.utcnow(False))

    def _convert_alarm_rule_change_event(self, event):
        """handle alarm rule change notification

        example of changed rule:
        "detail": {"severity": "critical",
                   "rule":
                       {"query": [{"field": "traits.resource_id",
                                   "type": "",
                                   "value": "1",
                                   "op": "eq"}],
                       "event_type": "instance.update"}}
        """
        old_alarm = self._old_alarm(event)
        entity = old_alarm.copy()

        changed_rule = event[CeilProps.DETAIL]
        for (changed_type, changed_info) in changed_rule.items():
            # handle changed rule which may effect the neighbor
            if changed_type == CeilProps.RULE:
                entity.update(self._parse_changed_rule(
                    changed_rule[changed_type]))
            # handle other changed alarm properties
            elif changed_type in vars(CeilProps).values():
                entity[changed_type] = changed_info

        return self._filter_and_cache_alarm(entity, old_alarm,
                                            self._filter_get_erroneous,
                                            datetime_utils.utcnow(False))

    def _convert_alarm_state_transition_event(self, event):

        old_alarm = self._old_alarm(event)
        entity = old_alarm.copy()
        try:
            entity[CeilProps.STATE] = event[CeilProps.DETAIL][CeilProps.STATE]
        except Exception:
            LOG.exception("Failed to Convert alarm state transition event.")

        return self._filter_and_cache_alarm(entity, old_alarm,
                                            self._filter_get_change,
                                            datetime_utils.utcnow(False))

    def _convert_alarm_deletion_event(self, event):
        alarm_key = self._alarm_key(event)
        alarm = self.cache.pop(alarm_key)[0]
        return alarm if self._is_erroneous(alarm) else None


def _parse_query(data, key):
    query_fields = data.get(CeilProps.QUERY, {})
    for query in query_fields:
        field = query['field']
        if field == key:
            return query['value']
    return None


def _is_vitrage_alarm(rule):
    return _parse_query(rule, CeilProps.VITRAGE_ID) is not None
