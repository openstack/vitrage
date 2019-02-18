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


class AodhProperties(object):
    ALARM_ID = 'alarm_id'
    DESCRIPTION = 'description'
    ENABLED = 'enabled'
    EVENT = 'event'
    EVENT_RULE = 'event_rule'
    EVENT_TYPE = 'event_type'
    EVENT_RESOURCE_ID = 'traits.resource_id'
    NAME = 'name'
    STATE = 'state'
    PROJECT_ID = 'project_id'
    QUERY = 'query'
    REPEAT_ACTIONS = 'repeat_actions'
    RESOURCE_ID = 'resource_id'
    SEVERITY = 'severity'
    STATE_TIMESTAMP = 'state_timestamp'
    THRESHOLD = 'threshold'
    THRESHOLD_RULE = 'threshold_rule'
    GNOCCHI_RESOURCES_THRESHOLD = 'gnocchi_resources_threshold'
    TIMESTAMP = 'timestamp'
    TYPE = 'type'
    VITRAGE_ID = 'vitrage_id'
    DETAIL = 'detail'
    RULE = 'rule'
    GNOCCHI_RESOURCES_THRESHOLD_RULE = 'gnocchi_resources_threshold_rule'
    COMPOSITE_RULE = 'composite_rule'
    GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD_RULE = \
        'gnocchi_aggregation_by_resources_threshold_rule'
    GNOCCHI_AGGREGATION_BY_METRICS_THRESHOLD_RULE = \
        'gnocchi_aggregation_by_metrics_threshold_rule'
    USER_ID = 'user_id'
    STATE_REASON = 'state_reason'
    METRICS = 'metrics'
    TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'


class AodhState(object):
    OK = 'ok'
    ALARM = 'alarm'
    INSUFFICIENT_DATA = 'insufficient_data'


class AodhEventType(object):
    CREATION = 'alarm.creation'
    RULE_CHANGE = 'alarm.rule_change'
    STATE_TRANSITION = 'alarm.state_transition'
    DELETION = 'alarm.deletion'


class AodhExtendedAlarmType(object):
    EVENT = 'event'
    VITRAGE = 'vitrage'
    THRESHOLD = 'threshold'
    GNOCCHI_RESOURCES_THRESHOLD = 'gnocchi_resources_threshold'
    COMPOSITE = 'composite'
    GNOCCHI_AGGREGATION_BY_METRICS_THRESHOLD =  \
        'gnocchi_aggregation_by_metrics_threshold'
    GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD = \
        'gnocchi_aggregation_by_resources_threshold'
