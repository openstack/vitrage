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

import copy

from copy import deepcopy
from oslo_log import log
from oslo_utils import importutils

from vitrage.common.constants import DatasourceAction as AType
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import VertexProperties as VProps
from vitrage.evaluator.actions.base import ActionMode
from vitrage.evaluator.actions.base import ActionType
from vitrage.evaluator.actions.evaluator_event_transformer \
    import VITRAGE_DATASOURCE
from vitrage.evaluator.actions.notifier import EvaluatorNotifier
from vitrage.evaluator.actions.recipes.action_steps import ADD_EDGE
from vitrage.evaluator.actions.recipes.action_steps import ADD_VERTEX
from vitrage.evaluator.actions.recipes.action_steps import EXECUTE_EXTERNAL
from vitrage.evaluator.actions.recipes.action_steps import EXECUTION_ENGINE
from vitrage.evaluator.actions.recipes.action_steps import REMOVE_EDGE
from vitrage.evaluator.actions.recipes.action_steps import REMOVE_VERTEX
from vitrage.evaluator.actions.recipes.action_steps import UPDATE_VERTEX
from vitrage.evaluator.actions.recipes.add_causal_relationship import \
    AddCausalRelationship
from vitrage.evaluator.actions.recipes.base import EVALUATOR_EVENT_TYPE
from vitrage.evaluator.actions.recipes.execute_mistral import ExecuteMistral
from vitrage.evaluator.actions.recipes.mark_down import MarkDown
from vitrage.evaluator.actions.recipes.raise_alarm import RaiseAlarm
from vitrage.evaluator.actions.recipes.set_state import SetState
from vitrage.utils import datetime as datetime_utils

LOG = log.getLogger(__name__)

EVALUATOR_EVENT = 'evaluator.event'
TARGET = 'target'
SOURCE = 'source'


class ActionExecutor(object):

    def __init__(self, actions_callback):

        self.actions_callback = actions_callback
        self.notifier = EvaluatorNotifier()
        self.action_recipes = ActionExecutor._register_action_recipes()

        self.action_step_defs = {
            ADD_VERTEX: self._add_vertex,
            REMOVE_VERTEX: self._remove_vertex,
            UPDATE_VERTEX: self._update_vertex,
            ADD_EDGE: self._add_edge,
            REMOVE_EDGE: self._remove_edge,
            EXECUTE_EXTERNAL: self._execute_external,
        }

    def execute(self, actions):
        if not actions:
            return

        events = []
        for action in actions:
            LOG.info('Action: %s', self._action_str(action))
            events.extend(self._execute(action.specs, action.mode))
        self.actions_callback(EVALUATOR_EVENT, events)

    def _execute(self, action_spec, action_mode):

        action_recipe = self.action_recipes[action_spec.type]
        if action_mode == ActionMode.DO:
            steps = action_recipe.get_do_recipe(action_spec)
        else:
            steps = action_recipe.get_undo_recipe(action_spec)

        events = []
        for step in steps:
            event = self.action_step_defs[step.type](step.params)
            if event:
                events.append(event)
        return events

    def _add_vertex(self, params):

        event = copy.deepcopy(params)
        ActionExecutor._add_default_properties(event)
        event[EVALUATOR_EVENT_TYPE] = ADD_VERTEX

        return event

    def _update_vertex(self, params):

        event = copy.deepcopy(params)
        ActionExecutor._add_default_properties(event)
        event[EVALUATOR_EVENT_TYPE] = UPDATE_VERTEX

        return event

    def _remove_vertex(self, params):
        event = copy.deepcopy(params)
        ActionExecutor._add_default_properties(event)
        event[EVALUATOR_EVENT_TYPE] = REMOVE_VERTEX

        return event

    def _add_edge(self, params):

        event = copy.deepcopy(params)
        ActionExecutor._add_default_properties(event)
        event[EVALUATOR_EVENT_TYPE] = ADD_EDGE

        return event

    def _remove_edge(self, params):

        event = copy.deepcopy(params)
        ActionExecutor._add_default_properties(event)
        event[EVALUATOR_EVENT_TYPE] = REMOVE_EDGE

        return event

    def _execute_external(self, params):

        # Send a notification to the external engine
        execution_engine = params[EXECUTION_ENGINE]
        payload = deepcopy(params)
        del payload[EXECUTION_ENGINE]

        LOG.debug('Notifying external engine %s. Properties: %s',
                  execution_engine,
                  payload)
        self.notifier.notify(execution_engine, payload)

    @staticmethod
    def _add_default_properties(event):

        event[DSProps.DATASOURCE_ACTION] = AType.UPDATE
        event[DSProps.ENTITY_TYPE] = VITRAGE_DATASOURCE
        event[VProps.UPDATE_TIMESTAMP] = str(datetime_utils.utcnow(False))
        event[VProps.VITRAGE_SAMPLE_TIMESTAMP] = datetime_utils.format_utcnow()

    @staticmethod
    def _register_action_recipes():

        # noinspection PyDictCreation
        recipes = {}

        recipes[ActionType.SET_STATE] = importutils.import_object(
            "%s.%s" % (SetState.__module__, SetState.__name__))

        recipes[ActionType.RAISE_ALARM] = importutils.import_object(
            "%s.%s" % (RaiseAlarm.__module__, RaiseAlarm.__name__))

        recipes[ActionType.ADD_CAUSAL_RELATIONSHIP] = \
            importutils.import_object(
            "%s.%s" % (AddCausalRelationship.__module__,
                       AddCausalRelationship.__name__))

        recipes[ActionType.MARK_DOWN] = importutils.import_object(
            "%s.%s" % (MarkDown.__module__, MarkDown.__name__))

        recipes[ActionType.EXECUTE_MISTRAL] = importutils.import_object(
            "%s.%s" % (ExecuteMistral.__module__, ExecuteMistral.__name__))

        return recipes

    @staticmethod
    def _action_str(action):
        s = action.specs.targets.get(SOURCE, {}).get(VProps.VITRAGE_ID, '')
        t = action.specs.targets.get(TARGET, {}).get(VProps.VITRAGE_ID, '')
        return '%s %s \'%s\' targets (%s,%s)' % (action.mode.upper(),
                                                 action.specs.type,
                                                 action.action_id, s, t)
