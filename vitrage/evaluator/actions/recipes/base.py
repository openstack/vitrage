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
from collections import namedtuple


ActionStepWrapper = namedtuple('ActionStepWrapper', ['type', 'params'])


EVALUATOR_EVENT_TYPE = 'type'


class Recipe(object, metaclass=abc.ABCMeta):

    @staticmethod
    @abc.abstractmethod
    def get_do_recipe(action_spec):
        """Execute the action.

        :param action_spec: The action specification as described in the
        template. contains:
            1. type - action type e.g. raise_alarm. set_state, etc.
            2. targets - target element(s) in the graph
            3. properties - the action properties
        :type action_spec: ActionSpecs
        """
        pass

    @staticmethod
    @abc.abstractmethod
    def get_undo_recipe(action_spec):
        """Revert the action.

        :param action_spec: The action specification as described in the
        template. contains:
            1. type - action type e.g. raise_alarm. set_state, etc.
            2. targets - target element(s) in the graph
            3. properties - the action properties
        :type action_spec: ActionSpecs
        """
        pass
