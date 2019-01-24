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

from vitrage.evaluator.template_data import ActionSpecs
from vitrage.evaluator.template_fields import TemplateFields as TField


class ActionLoader(object):

    def load(self, action_id, default_target, action_dict, action_type):
        """V3 template action to ActionSpecs transformation

        :param action_id: Unique action identifier
        :param default_target: Is taken from the condition,
         it is used when the action doesn't define a target
        :param action_dict: Action section taken from the template.
        :param action_type: example: set_state/raise_alarm/etc..
        :rtype: ActionSpecs
        """
        target = action_dict.pop(TField.TARGET, default_target[TField.TARGET])
        targets = {TField.TARGET: target}
        if action_dict.get(TField.SOURCE):
            targets[TField.SOURCE] = action_dict.pop(TField.SOURCE)
        return ActionSpecs(action_id, action_type, targets, action_dict)
