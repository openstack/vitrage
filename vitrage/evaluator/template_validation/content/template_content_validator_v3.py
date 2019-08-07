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
from sympy import Not
from sympy import Symbol

from vitrage.evaluator.base import get_template_schema
from vitrage.evaluator import condition as dnf

from vitrage.evaluator.template_fields import TemplateFields
from vitrage.evaluator.template_functions import function_resolver
from vitrage.evaluator.template_functions import GET_PARAM
from vitrage.evaluator.template_functions.v2.functions import get_param
from vitrage.evaluator.template_loading.template_loader_v3 import \
    TemplateLoader as V3TemplateLoader
from vitrage.evaluator.template_validation.base import ValidationError

LOG = log.getLogger(__name__)

RELATION = 'relationship'


class ContentValidator(object):

    @staticmethod
    def validate(template, actual_params):
        _validate_entities_regex(template)
        _validate_conditions(template)
        _validate_parameters(template, actual_params)

        # As part of validation, when it is finished,
        # we try to load the template, as some validations can only be
        # executed at loading phase
        schema = get_template_schema(template)
        V3TemplateLoader().load(schema, template)


def _validate_entities_regex(template):
    for entity in template[TemplateFields.ENTITIES].values():
        for key, value in entity.items():
            if key.lower().endswith(TemplateFields.REGEX):
                try:
                    re.compile(value)
                except Exception:
                    raise ValidationError(47, key, value)


def _validate_conditions(template):
    """Validate conditions

    'alarm_1 [on] host AND host [contains] instance AND alarm_2 [on] instance
     AND host'
    In this condition , replace all occurrences of 'source [label] target'
    so to create :
    'relationship AND relationship AND relationship AND host'
    """
    for scenario in template[TemplateFields.SCENARIOS]:
        condition = scenario[TemplateFields.CONDITION]
        _validate_condition_entity_ids(template, condition)
        _validate_not_condition(condition)


def _validate_parameters(template, actual_params):
    function_resolver.validate_function(
        func_info=function_resolver.FuncInfo(
            name=GET_PARAM, func=get_param, error_code=160),
        template=template,
        actual_params=actual_params)


def _validate_condition_entity_ids(template, condition):
    curr_str = ' ' + condition + ' '

    # Remove all [label] occurrences
    edge_labels_re = r'\s+\[\s*\w+\s*\]\s+'
    curr_str = re.sub(edge_labels_re, ' ', curr_str)
    if '[' in curr_str or ']' in curr_str:
        raise ValidationError(85, condition)

    # Remove all operator occurrences
    operators_re = r'\b(AND|OR|NOT|and|or|not)\b'
    curr_str = re.sub(operators_re, '', curr_str)

    # Remove all entity occurrences
    for entity_id in template[TemplateFields.ENTITIES].keys():
        entity_id_regex = r'\b' + entity_id + r'\b'
        curr_str = re.sub(entity_id_regex, ' ', curr_str)

    # Remove all parentheses occurrences
    curr_str = curr_str.replace('(', '')
    curr_str = curr_str.replace(')', '')

    # Remaining string should be empty
    if curr_str.strip():
        raise ValidationError(10200, condition, curr_str)


def _validate_not_condition(condition):
    """Not operator validation

    1. Not operator can appear only on relationships.
    2. There must be at least one  positive term
    """
    regex = r"(\w+)\s*\[\s*(\w+)\s*\]\s*(\w+)"
    preprocessed_condition = re.sub(regex, RELATION, condition)

    try:
        dnf_condition = dnf.convert_to_dnf_format(preprocessed_condition)
        _validate_not_condition_relationships_recursive(dnf_condition)
        dnf_condition = dnf.parse_condition(preprocessed_condition)
        _validate_positive_term_in_condition(dnf_condition)
    except ValidationError as e:
        raise ValidationError(e.code, e.details, condition)
    except Exception as e:
        raise ValidationError(85, condition, e)


def _validate_not_condition_relationships_recursive(dnf_result):
    if isinstance(dnf_result, Not):
        for arg in dnf_result.args:
            if isinstance(arg, Symbol) and not str(arg).startswith(RELATION):
                raise ValidationError(86, arg)
            else:
                _validate_not_condition_relationships_recursive(arg)
        return

    for arg in dnf_result.args:
        if not isinstance(arg, Symbol):
            _validate_not_condition_relationships_recursive(arg)


def _validate_positive_term_in_condition(dnf_condition):
    if not dnf.is_condition_include_positive_clause(dnf_condition):
        raise ValidationError(134)
