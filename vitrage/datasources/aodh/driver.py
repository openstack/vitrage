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
import json

from oslo_log import log

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.datasources.alarm_driver_base import AlarmDriverBase
from vitrage.datasources.aodh import AODH_DATASOURCE
from vitrage.datasources.aodh.properties import AodhEventType
from vitrage.datasources.aodh.properties import AodhExtendedAlarmType
from vitrage.datasources.aodh.properties import AodhProperties as AodhProps
from vitrage.datasources.aodh.properties import AodhState
from vitrage import os_clients
from vitrage.utils import datetime as datetime_utils

LOG = log.getLogger(__name__)


class AodhDriver(AlarmDriverBase):

    def __init__(self):
        super(AodhDriver, self).__init__()
        self._client = None
        self._init_aodh_event_actions()
        self._init_convert_aodh_alarm_rule_actions()
        self._init_alarm_type_to_rule()
        self._cache_all_alarms()

    def _init_aodh_event_actions(self):
        self.actions = {
            AodhEventType.CREATION: self._convert_alarm_creation_event,
            AodhEventType.RULE_CHANGE: self._convert_alarm_rule_change_event,
            AodhEventType.STATE_TRANSITION:
                self._convert_alarm_state_transition_event,
            AodhEventType.DELETION: self._convert_alarm_deletion_event
        }

    def _init_convert_aodh_alarm_rule_actions(self):
        self.convert_rule_actions = {
            AodhExtendedAlarmType.VITRAGE:
                self._convert_vitrage_alarm_rule,
            AodhExtendedAlarmType.EVENT:
                self._convert_event_alarm_rule,
            AodhExtendedAlarmType.THRESHOLD:
                self._convert_threshold_alarm_rule,
            AodhExtendedAlarmType.GNOCCHI_RESOURCES_THRESHOLD:
                self._convert_gnocchi_resources_threshold_alarm_rule,
            AodhExtendedAlarmType.GNOCCHI_AGGREGATION_BY_METRICS_THRESHOLD:
                self._convert_gnocchi_aggregation_by_metrics_threshold_rule,
            AodhExtendedAlarmType.GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD:
                self._convert_gnocchi_aggregation_by_resources_threshold_rule,
            AodhExtendedAlarmType.COMPOSITE:
                self._convert_composite_alarm_rule

        }

    def _init_alarm_type_to_rule(self):
        self.alarm_rule_types = {
            AodhExtendedAlarmType.VITRAGE: AodhProps.EVENT_RULE,
            AodhExtendedAlarmType.EVENT: AodhProps.EVENT_RULE,
            AodhExtendedAlarmType.THRESHOLD: AodhProps.THRESHOLD_RULE,
            AodhExtendedAlarmType.GNOCCHI_RESOURCES_THRESHOLD:
                AodhProps.GNOCCHI_RESOURCES_THRESHOLD_RULE,
            AodhExtendedAlarmType.COMPOSITE: AodhProps.COMPOSITE_RULE,
            AodhExtendedAlarmType.GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD:
                AodhProps.GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD_RULE,
            AodhExtendedAlarmType.GNOCCHI_AGGREGATION_BY_METRICS_THRESHOLD:
                AodhProps.GNOCCHI_AGGREGATION_BY_METRICS_THRESHOLD_RULE
        }

    @property
    def client(self):
        if not self._client:
            self._client = os_clients.aodh_client()
        return self._client

    def _vitrage_type(self):
        return AODH_DATASOURCE

    def _alarm_key(self, alarm):
        return alarm[AodhProps.ALARM_ID]

    def _cache_all_alarms(self):
        alarms = self._get_alarms()
        self._filter_and_cache_alarms(alarms,
                                      self._filter_get_valid)

    def _get_alarms(self):
        try:
            aodh_alarms = self.client.alarm.list()
            return [self._convert_alarm(alarm) for alarm in
                    aodh_alarms if alarm is not None]
        except Exception:
            LOG.exception("Failed to get all alarms.")
        return []

    def _is_erroneous(self, alarm):
        return alarm and alarm[AodhProps.STATE] == AodhState.ALARM

    def _status_changed(self, alarm1, alarm2):
        return alarm1 and alarm2 and \
            not alarm1[AodhProps.STATE] == alarm2[AodhProps.STATE]

    def _is_valid(self, alarm):
        return True

    def _get_aodh_alarm_type(self, alarm):

        Aodh_type = [AodhExtendedAlarmType.EVENT,
                     AodhExtendedAlarmType.THRESHOLD,
                     AodhExtendedAlarmType.GNOCCHI_RESOURCES_THRESHOLD,
                     AodhExtendedAlarmType.
                     GNOCCHI_AGGREGATION_BY_METRICS_THRESHOLD,
                     AodhExtendedAlarmType.
                     GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD,
                     AodhExtendedAlarmType.COMPOSITE]

        alarm_type = alarm[AodhProps.TYPE]
        if alarm_type == AodhProps.EVENT and \
                _is_vitrage_alarm(alarm.get(AodhProps.EVENT_RULE)
                                  or alarm.get(AodhProps.RULE)):
            return AodhExtendedAlarmType.VITRAGE
        elif alarm_type not in Aodh_type:
            LOG.warning('Unsupported Aodh alarm of type %s' % alarm_type)
            alarm_type = None

        return alarm_type

    def _convert_alarm(self, alarm):

        entity = self._convert_alarm_common(alarm)

        detail = self._convert_alarm_detail(alarm)
        entity.update(detail)

        alarm_type = self._get_aodh_alarm_type(alarm)
        alarm_rule_type = self.alarm_rule_types[alarm_type]
        alarm_rule = alarm[alarm_rule_type]
        rule = self._convert_alarm_rule(alarm_type, alarm_rule)
        entity.update(rule)

        return entity

    @staticmethod
    def get_event_types():
        # Add event_types to receive notifications about
        return [AodhEventType.CREATION,
                AodhEventType.STATE_TRANSITION,
                AodhEventType.RULE_CHANGE,
                AodhEventType.DELETION]

    def enrich_event(self, event, event_type):
        if event_type in self.actions:
            entity = self.actions[event_type](event)
        else:
            LOG.warning('Unsupported Aodh event type %s' % event_type)
            return None

        # Don't need to update entity, only update the cache
        if entity is None:
            return None

        entity[DSProps.EVENT_TYPE] = event_type

        return AodhDriver.make_pickleable([entity],
                                          AODH_DATASOURCE,
                                          DatasourceAction.UPDATE)[0]

    @classmethod
    def _convert_vitrage_alarm_rule(cls, rule):
        return {
            AodhProps.VITRAGE_ID: _parse_query(rule, AodhProps.VITRAGE_ID),
            AodhProps.RESOURCE_ID: _parse_query(rule, AodhProps.RESOURCE_ID)
        }

    @classmethod
    def _convert_threshold_alarm_rule(cls, rule):
        return cls._alarm_rule_common(rule)

    @classmethod
    def _convert_gnocchi_resources_threshold_alarm_rule(cls, rule):
        return {
            AodhProps.RESOURCE_ID: rule[AodhProps.RESOURCE_ID]
        }

    @classmethod
    def _convert_gnocchi_aggregation_by_metrics_threshold_rule(cls, rule):
        return cls._alarm_rule_common(rule)

    @classmethod
    def _convert_gnocchi_aggregation_by_resources_threshold_rule(cls, rule):
        return cls._alarm_rule_common(rule)

    @classmethod
    def _convert_composite_alarm_rule(cls, rule):
        return cls._alarm_rule_common(rule)

    @classmethod
    def _alarm_rule_common(cls, rule):
        return {
            AodhProps.RESOURCE_ID: _parse_query(rule, AodhProps.RESOURCE_ID)
        }

    @classmethod
    def _convert_event_alarm_rule(cls, rule):
        return {
            AodhProps.EVENT_TYPE: rule[AodhProps.EVENT_TYPE],
            AodhProps.RESOURCE_ID:
                _parse_query(rule, AodhProps.EVENT_RESOURCE_ID)
        }

    @classmethod
    def _convert_alarm_common(cls, alarm):
        return {
            AodhProps.ALARM_ID: alarm.get(AodhProps.ALARM_ID),
            AodhProps.USER_ID: alarm.get(AodhProps.USER_ID),
            AodhProps.PROJECT_ID: alarm.get(AodhProps.PROJECT_ID),
            AodhProps.SEVERITY: alarm.get(AodhProps.SEVERITY),
            AodhProps.TIMESTAMP: alarm.get(AodhProps.TIMESTAMP)
        }

    @classmethod
    def _convert_alarm_detail(cls, alarm):

        return {
            AodhProps.DESCRIPTION: alarm.get(AodhProps.DESCRIPTION),
            AodhProps.ENABLED: alarm.get(AodhProps.ENABLED),
            AodhProps.NAME: alarm.get(AodhProps.NAME),
            AodhProps.STATE: alarm.get(AodhProps.STATE),
            AodhProps.REPEAT_ACTIONS: alarm.get(AodhProps.REPEAT_ACTIONS),
            AodhProps.TYPE: alarm.get(AodhProps.TYPE),
            AodhProps.STATE_TIMESTAMP: alarm.get(AodhProps.STATE_TIMESTAMP),
            AodhProps.STATE_REASON: alarm.get(AodhProps.STATE_REASON)
        }

    def _convert_alarm_rule(self, alarm_type, alarm_rule):
        if alarm_type in self.convert_rule_actions:
            entity = self.convert_rule_actions[alarm_type](alarm_rule)
        else:
            LOG.warning('Unsupported Aodh alarm type %s' % alarm_type)
            return None

        return entity

    @classmethod
    def _parse_changed_rule(cls, change_rule):
        entity = {}
        if AodhProps.EVENT_TYPE in change_rule:
            entity[AodhProps.EVENT_TYPE] = change_rule[AodhProps.EVENT_TYPE]
        if 'query' in change_rule:
            event_resource_id = \
                _parse_query(change_rule, AodhProps.EVENT_RESOURCE_ID)
            resource_id = \
                _parse_query(change_rule, AodhProps.RESOURCE_ID)
            if event_resource_id or resource_id:
                entity[AodhProps.RESOURCE_ID] = event_resource_id if \
                    event_resource_id is not None else resource_id

        return entity

    @staticmethod
    def should_delete_outdated_entities():
        return True

    def _convert_alarm_creation_event(self, event):
        entity = self._convert_alarm_common(event)

        alarm_info = event[AodhProps.DETAIL]
        detail = self._convert_alarm_detail(alarm_info)
        entity.update(detail)

        alarm_type = self._get_aodh_alarm_type(alarm_info)
        alarm_rule = alarm_info[AodhProps.RULE]
        rule_info = self._convert_alarm_rule(alarm_type, alarm_rule)
        entity.update(rule_info)

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
        changed_rule = event[AodhProps.DETAIL]
        for (changed_type, changed_info) in changed_rule.items():
            # handle changed rule which may effect the neighbor
            if changed_type == AodhProps.RULE:
                entity.update(self._parse_changed_rule(
                    changed_rule[changed_type]))
            # handle other changed alarm properties
            elif changed_type in vars(AodhProps).values():
                entity[changed_type] = changed_info

        return self._filter_and_cache_alarm(entity, old_alarm,
                                            self._filter_get_erroneous,
                                            datetime_utils.utcnow(False))

    def _convert_alarm_state_transition_event(self, event):

        old_alarm = self._old_alarm(event)
        entity = old_alarm.copy()
        try:
            entity[AodhProps.STATE] = event[AodhProps.DETAIL][AodhProps.STATE]
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
    """Find the relevant key in a given alarm detail query.

    :param data: A query is either a list of this form:
    [
        {
        field: resource_id,
        value: 54132
        }
    ]
    or a string-represented dict of this form:
    '{
        =: { resource_id : 1235423 }
     }'
    """

    query_fields = data.get(AodhProps.QUERY, {})
    try:
        if isinstance(query_fields, str):
            query_fields = json.loads(query_fields)
        if not isinstance(query_fields, list):
            query_fields = [query_fields]
        for query in query_fields:
            field = query.get('field')
            if field and field == key:
                return query['value']
            elif not field:
                field = query.get('=', {})
                for k in field:
                    if k == key:
                        return field[key]
        return None

    except Exception:
        LOG.exception("Failed to parse AODH alarm query")
        return None


def _is_vitrage_alarm(rule):
    return _parse_query(rule, AodhProps.VITRAGE_ID) is not None
