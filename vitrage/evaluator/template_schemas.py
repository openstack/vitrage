# Copyright 2017 - Nokia
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
from oslo_log import log

from vitrage.evaluator.actions.base import ActionType
from vitrage.evaluator.template_fields import TemplateFields
from vitrage.evaluator.template_functions.v2.functions import get_attr
from vitrage.evaluator.template_functions.v2.functions import GET_ATTR
from vitrage.evaluator.template_loading.v1.action_loader import ActionLoader
from vitrage.evaluator.template_loading.v1.execute_mistral_loader import \
    ExecuteMistralLoader
from vitrage.evaluator.template_validation.content.v1.\
    add_causal_relationship_validator import AddCausalRelationshipValidator
from vitrage.evaluator.template_validation.content.v1.definitions_validator \
    import DefinitionsValidator
from vitrage.evaluator.template_validation.content.v1.\
    execute_mistral_validator import ExecuteMistralValidator as \
    V1ExecuteMistralValidator
from vitrage.evaluator.template_validation.content.v1.mark_down_validator \
    import MarkDownValidator
from vitrage.evaluator.template_validation.content.v1.raise_alarm_validator \
    import RaiseAlarmValidator
from vitrage.evaluator.template_validation.content.v1.scenario_validator \
    import ScenarioValidator
from vitrage.evaluator.template_validation.content.v1.set_state_validator \
    import SetStateValidator
from vitrage.evaluator.template_validation.content.v2.\
    execute_mistral_validator import ExecuteMistralValidator as \
    V2ExecuteMistralValidator
from vitrage.evaluator.template_schema_factory import TemplateSchemaFactory

LOG = log.getLogger(__name__)


class TemplateSchema1(object):
    def __init__(self):
        self.validators = {
            TemplateFields.DEFINITIONS: DefinitionsValidator,
            TemplateFields.SCENARIOS: ScenarioValidator,
            ActionType.ADD_CAUSAL_RELATIONSHIP: AddCausalRelationshipValidator,
            ActionType.EXECUTE_MISTRAL: V1ExecuteMistralValidator,
            ActionType.MARK_DOWN: MarkDownValidator,
            ActionType.RAISE_ALARM: RaiseAlarmValidator,
            ActionType.SET_STATE: SetStateValidator,
        }

        self.loaders = {
            ActionType.ADD_CAUSAL_RELATIONSHIP: ActionLoader(),
            ActionType.EXECUTE_MISTRAL: ExecuteMistralLoader(),
            ActionType.MARK_DOWN: ActionLoader(),
            ActionType.RAISE_ALARM: ActionLoader(),
            ActionType.SET_STATE: ActionLoader(),
        }

        self.functions = {}

    def version(self):
        return '1'


class TemplateSchema2(TemplateSchema1):

    def __init__(self):
        super(TemplateSchema2, self).__init__()
        self.validators[ActionType.EXECUTE_MISTRAL] = \
            V2ExecuteMistralValidator()
        self.loaders[ActionType.EXECUTE_MISTRAL] = ActionLoader()
        self.functions[GET_ATTR] = get_attr

    def version(self):
        return '2'


def init_template_schemas():
    TemplateSchemaFactory.register_template_schema('1', TemplateSchema1())
    TemplateSchemaFactory.register_template_schema('2', TemplateSchema2())
