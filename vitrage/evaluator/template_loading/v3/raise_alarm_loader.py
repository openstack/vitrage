# Copyright 2019 - Nokia
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

from vitrage.evaluator.template_fields import TemplateFields as TField
from vitrage.evaluator.template_loading.v3.action_loader import ActionLoader


class RaiseAlarmLoader(ActionLoader):

    def load(self, action_id, default_target, action_dict, action_type):
        """V3 template action raise_alarm to ActionSpecs transformation

        causing_alarm is replaced with a function, to get the vertex id.
        Example:
        causing_alarm: zabbix_alarm
        Replaced with:
        causing_alarm: get_attr(zabbix_alarm, vitrage_id)

        :param action_id: Unique action identifier
        :param default_target: Is taken from the condition,
         it is used when the action doesn't define a target
        :param action_dict: Action section taken from the template.
        :param action_type: example: set_state/raise_alarm/etc..
        :rtype: ActionSpecs
        """
        if TField.CAUSING_ALARM in action_dict:
            action_dict[TField.CAUSING_ALARM] = \
                'get_attr(%s, vitrage_id)' % action_dict[TField.CAUSING_ALARM]
        return super(RaiseAlarmLoader, self).load(
            action_id, default_target, action_dict, action_type)
