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

from vitrage.common.constants import TemplateTopologyFields


class TemplateFields(TemplateTopologyFields):

    SCENARIOS = 'scenarios'
    PARAMETERS = 'parameters'

    ALARM_NAME = 'alarm_name'
    ACTION = 'action'
    ACTIONS = 'actions'
    ACTION_TARGET = 'action_target'
    ACTION_TYPE = 'action_type'
    CATEGORY = 'category'
    CAUSING_ALARM = 'causing_alarm'
    CONDITION = 'condition'
    INCLUDES = 'includes'
    SEVERITY = 'severity'
    SCENARIO = 'scenario'
    STATE = 'state'
    TEMPLATE_ID = 'template_id'

    PROPERTIES = 'properties'
    REGEX = '.regex'
    DEFAULT = 'default'
