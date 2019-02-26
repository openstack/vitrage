# Copyright 2016 - Nokia
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
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import TemplateTypes
from vitrage.evaluator.actions.base import action_types
from vitrage.evaluator.template_schema_factory import TemplateSchemaFactory


status_msgs = {

    # General 1-19
    0: 'Template validation is OK',
    1: 'template_id field contains incorrect string value.',
    2: 'Duplicate template_id definition.',
    3: 'template_id does not appear in the definition block.',
    4: 'Syntax error: ',
    5: 'Invalid yaml format: ',

    # definitions section 20-39
    20: 'definitions section must contain entities field.',
    21: 'definitions section is a mandatory section.',

    # Entities status messages 40-59
    41: 'Entity definition must contain template_id field.',
    42: 'Entity definition must contain category field.',
    43: 'At least one entity must be defined.',
    45: 'Invalid entity category. Category must be from types: '
        '{categories}'.format(categories=EntityCategory.categories()),
    46: 'Entity field is required.',
    47: 'Invalid regular expression defined in field:',

    # metadata section status messages 60-79
    60: 'metadata section must contain id field.',
    62: 'metadata is a mandatory section.',
    63: 'Unsupported version. Version must be one of: {versions}'
        .format(versions=TemplateSchemaFactory.supported_versions()),
    64: 'metadata section must contain a type field starting from version 2. '
        'Type must be one of: {types}'.format(types=TemplateTypes.types()),
    65: 'Invalid template type. Type must be one of: {types}'
        .format(types=TemplateTypes.types()),
    66: 'Missing template type. Type must be one of: {types}'
        .format(types=TemplateTypes.types()),

    # scenarios section status messages 80-99
    80: 'scenarios is a mandatory section.',
    81: 'At least one scenario must be defined.',
    82: 'scenario field is required.',
    83: 'Scenario definition must contain condition field.',
    84: 'Scenario definition must contain actions field.',
    85: 'Failed to convert condition.',
    86: 'Not operator can be used only on relationships.',

    # relationships status messages 100-119
    101: 'Relationship field is required.',
    102: 'Relationship definition must contain source field.',
    103: 'Relationship definition must contain target field.',
    104: 'Relationship definition must contain template_id field.',

    # actions status messages 120-139
    120: 'Invalid action type. Action type must be from types: '
         '{actions}'.format(actions=action_types),
    121: 'At least one action must be defined.',
    122: 'Action field is required.',
    123: 'Action definition must contain action_type field.',
    124: 'Action definition must contain action_target field.',
    125: 'raise_alarm action must contain alarm_name field in properties '
         'block.',
    126: 'raise_alarm action must contain severity field in properties block.',
    127: 'raise_alarm action must contain target field in target_action block',
    128: 'set_state action must contain state field in properties block.',
    129: 'set_state action must contain target field in target_action block.',
    130: 'add_causal_relationship action must contain target and source field '
         'in target_action block.',
    131: 'mark_down action must contain \'target\' field in'
         ' \'target_action\' block.',
    132: 'add_causal_relationship action requires action_target to be ALARM',
    133: 'execute_mistral action must contain workflow field in properties '
         'block',
    134: 'condition can not contain only \'not\' clauses',
    135: 'condition must contain a common entity for all \'or\' clauses',
    136: 'Input parameters for the Mistral workflow in execute_mistral action '
         'must be placed under an \'input\' block ',
    137: 'Functions are supported only from version 2',
    138: 'Only open or close parenthesis exists. Did you try to use '
         'a function?',

    # def_templates status messages 140-159
    140: 'At least one template must be included',
    141: 'Name field is unspecified for include',
    142: 'Trying to include a template that does not exist',
    143: 'A template definition file cannot contain \'includes\' or '
         '\'scenarios\' blocks',

    # parameters status messages 160-179
    160: 'Parameters are supported only from version 2',
    161: 'get_param called for a parameter that is not defined in the '
         '\'parameters\' block',
    162: 'malformed get_param() clause',
    163: 'Failed to resolve parameter',

    # template version 3
    10100: 'Action must contain a \'target\' property',
    10101: 'Action \'target\' must match an entity id',
    10102: 'Action must contain a \'source\' property',
    10103: 'Action \'source\' must match an entity id',
    10104: 'raise_alarm action must contain an \'alarm_name\' property',
    10105: 'execute_mistral action must contain \'workflow\' property',
    10107: 'The property \'causing_alarm\' in raise_alarm action must match an'
           ' entity id',
    10200: 'Condition contains an unknown entity id',
}
