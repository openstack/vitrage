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


class ActionType(object):

    SET_STATE = 'set_state'
    RAISE_ALARM = 'raise_alarm'
    ADD_CAUSAL_RELATIONSHIP = 'add_causal_relationship'
    MARK_DOWN = 'mark_down'
    EXECUTE_MISTRAL = 'execute_mistral'


action_types = [ActionType.SET_STATE,
                ActionType.RAISE_ALARM,
                ActionType.ADD_CAUSAL_RELATIONSHIP,
                ActionType.MARK_DOWN,
                ActionType.EXECUTE_MISTRAL]


class ActionMode(object):
    DO = 'do'
    UNDO = 'undo'
