# Copyright 2019 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import re

from oslo_log import log
from voluptuous import Any
from voluptuous import In
from voluptuous import Invalid
from voluptuous import Optional
from voluptuous import Required
from voluptuous import Schema

from vitrage.common.constants import TemplateTypes
from vitrage.evaluator.actions.base import ActionType
from vitrage.evaluator.actions.recipes.execute_mistral import INPUT
from vitrage.evaluator.actions.recipes.execute_mistral import WORKFLOW
from vitrage.evaluator.template_fields import TemplateFields as TF
from vitrage.evaluator.template_functions.function_resolver import is_function
from vitrage.evaluator.template_schema_factory import TemplateSchemaFactory

LOG = log.getLogger(__name__)


any_str = Any(str)


class SyntaxValidator(object):

    @staticmethod
    def validate(template):
        Schema({
            Required(TF.ENTITIES, msg=10000): _entities_schema(),
            Required(TF.METADATA, msg=62): _metadata_schema(),
            Required(TF.SCENARIOS, msg=80): _scenarios_schema(template),
            Optional(TF.PARAMETERS): _parameters_schema(),
        })(template)


def _entities_schema():
    return Schema({
        any_str: Schema({
            any_str: any_str,
        })})


def _metadata_schema():
    return Schema({
        Required(TF.VERSION, msg=63): In(
            TemplateSchemaFactory.supported_versions()),
        Required(TF.NAME, msg=60): any_str,
        TF.DESCRIPTION: any_str,
        Required(TF.TYPE, msg=64): In(TemplateTypes.types(), msg=64),
    })


def _scenarios_schema(template):

    return Schema([
        Schema({
            Required(TF.ACTIONS, msg=84): Schema([Any(
                _raise_alarm_schema(template),
                _set_state_schema(template),
                _add_causal_relationship_schema(template),
                _mark_down_schema(template),
                _execute_mistral_schema(),
            )]),
            Required(TF.CONDITION, msg=83): any_str,
        })])


def _parameters_schema():
    return Schema({
        any_str: Any(any_str, Schema({
            Optional(TF.DESCRIPTION): any_str,
            Optional(TF.DEFAULT): any_str,
        })),
    })


def _raise_alarm_schema(template):
    return Schema({
        Optional(ActionType.RAISE_ALARM): Schema({
            Required(TF.SEVERITY, msg=126): any_str,
            Required(TF.TARGET, msg=10100):
                In(template.get(TF.ENTITIES, {}).keys(), msg=10101),
            Required(TF.ALARM_NAME, msg=10104): any_str,
            Optional(TF.CAUSING_ALARM):
                In(template.get(TF.ENTITIES, {}).keys(), msg=10107),
        })})


def _set_state_schema(template):
    return Schema({
        Optional(ActionType.SET_STATE): Schema({
            Required(TF.STATE, msg=128): any_str,
            Required(TF.TARGET, msg=10100):
                In(template.get(TF.ENTITIES, {}).keys(), msg=10101),
        })})


def _add_causal_relationship_schema(template):
    return Schema({
        Optional(ActionType.ADD_CAUSAL_RELATIONSHIP): Schema({
            Required(TF.SOURCE, msg=10102):
                In(template.get(TF.ENTITIES, {}).keys(), msg=10103),
            Required(TF.TARGET, msg=10100):
                In(template.get(TF.ENTITIES, {}).keys(), msg=10101),
        })})


def _mark_down_schema(template):
    return Schema({
        Optional(ActionType.MARK_DOWN): Schema({
            Required(TF.TARGET, msg=10100):
                In(template.get(TF.ENTITIES, {}).keys(), msg=10101),
        })})


def _execute_mistral_schema():

    return Schema({
        Optional(ActionType.EXECUTE_MISTRAL): Schema({
            Required(WORKFLOW, msg=10105): any_str,
            Optional(INPUT): Schema({
                any_str: IsProperFunction()}
            )})})


class IsProperFunction(object):
    """If Value contains parentheses, check it is a proper function call"""

    def __call__(self, v):
        if re.findall('[(),]', v) and not is_function(v):
            raise Invalid(138)
        return v
