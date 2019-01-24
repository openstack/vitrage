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

import abc

from vitrage.evaluator.template_data import ActionSpecs
from vitrage.evaluator.template_fields import TemplateFields as TFields


class BaseActionLoader(object):

    def load(self, action_id, default_target, action_def):
        action_dict = action_def[TFields.ACTION]
        action_type = action_dict[TFields.ACTION_TYPE]
        targets = action_dict.get(TFields.ACTION_TARGET, default_target)
        return ActionSpecs(action_id, action_type, targets,
                           self._get_properties(action_dict))

    @abc.abstractmethod
    def _get_properties(self, action_dict):
        pass


class ActionLoader(BaseActionLoader):
    def _get_properties(self, action_dict):
        return action_dict.get(TFields.PROPERTIES, {})
