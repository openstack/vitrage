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

from functools import reduce
from sympy.logic.boolalg import Not
from sympy import Symbol

from oslo_log import log

from vitrage.common.constants import EdgeProperties as EProps
from vitrage.evaluator.condition import convert_to_dnf_format
from vitrage.evaluator.condition import get_condition_common_targets
from vitrage.evaluator.condition import is_condition_include_positive_clause
from vitrage.evaluator.condition import parse_condition
from vitrage.evaluator.condition import SymbolResolver
from vitrage.evaluator.template_fields import TemplateFields
from vitrage.evaluator.template_validation.content.base import \
    get_content_correct_result
from vitrage.evaluator.template_validation.content.base import \
    get_content_fault_result
from vitrage.evaluator.template_validation.content.base import \
    validate_template_id
from vitrage.evaluator.template_validation.status_messages import status_msgs

LOG = log.getLogger(__name__)


class ScenarioValidator(object):

    class TemplateSymbolResolver(SymbolResolver):
        def is_relationship(self, symbol):
            return TemplateFields.RELATIONSHIP_TYPE in symbol

        def get_relationship_source_id(self, relationship):
            return relationship[TemplateFields.SOURCE]

        def get_relationship_target_id(self, relationship):
            return relationship[TemplateFields.TARGET]

        def get_entity_id(self, entity):
            return entity[TemplateFields.TEMPLATE_ID]

    @classmethod
    def validate(cls, template_schema, def_index, scenarios):
        for scenario in scenarios:
            scenario_values = scenario[TemplateFields.SCENARIO]

            condition = scenario_values[TemplateFields.CONDITION]
            result = cls._validate_scenario_condition(def_index, condition)

            if not result.is_valid_config:
                return result

            actions = scenario_values[TemplateFields.ACTIONS]
            result = cls._validate_scenario_actions(template_schema,
                                                    def_index, actions)

            if not result.is_valid_config:
                return result

        return get_content_correct_result()

    # noinspection PyBroadException
    @classmethod
    def _validate_scenario_condition(cls, def_index, condition):
        try:
            dnf_result = convert_to_dnf_format(condition)
        except Exception:
            LOG.error('%s status code: %s' % (status_msgs[85], 85))
            return get_content_fault_result(85)

        # not condition validation
        not_condition_result = cls._validate_not_condition(def_index,
                                                           dnf_result)
        if not not_condition_result.is_valid_config:
            return not_condition_result

        # template id validation
        values_to_replace = ' and ', ' or ', ' not ', 'not ', '(', ')'
        condition_vars = reduce(lambda cond, v: cond.replace(v, ' '),
                                values_to_replace,
                                condition)

        for condition_var in condition_vars.split(' '):

            if len(condition_var.strip()) == 0:
                continue

            result = \
                validate_template_id(def_index, condition_var)
            if not result.is_valid_config:
                return result

        # condition structure validation
        condition_structure_result = cls._validate_condition_structure(
            def_index, parse_condition(condition))
        if not condition_structure_result.is_valid_config:
            return condition_structure_result

        return get_content_correct_result()

    @classmethod
    def _validate_condition_structure(cls, def_index, condition_dnf):
        result = \
            cls._validate_condition_includes_positive_clause(condition_dnf)
        if not result.is_valid_config:
            return result

        common_targets = \
            get_condition_common_targets(condition_dnf,
                                         def_index,
                                         cls.TemplateSymbolResolver())

        return get_content_correct_result() if common_targets \
            else get_content_fault_result(135)

    @staticmethod
    def _validate_condition_includes_positive_clause(condition):
        return get_content_correct_result() if \
            is_condition_include_positive_clause(condition) \
            else get_content_fault_result(134)

    @classmethod
    def _validate_not_condition(cls, def_index, dnf_result):
        """Not operator validation

        Not operator can appear only on edges.

        :param dnf_result:
        :param def_index:
        :return:
        """

        if isinstance(dnf_result, Not):
            for arg in dnf_result.args:
                if isinstance(arg, Symbol):
                    definition = def_index.get(str(arg), None)
                    if not (definition and
                            definition.get(EProps.RELATIONSHIP_TYPE)):
                        msg = status_msgs[86] + ' template id: %s' % arg
                        LOG.error('%s status code: %s' % (msg, 86))
                        return get_content_fault_result(86, msg)
                else:
                    res = cls._validate_not_condition(def_index, arg)
                    if not res.is_valid_config:
                        return res
            return get_content_correct_result()

        for arg in dnf_result.args:
            if not isinstance(arg, Symbol):
                res = cls._validate_not_condition(def_index, arg)
                if not res.is_valid_config:
                    return res

        return get_content_correct_result()

    @classmethod
    def _validate_scenario_actions(cls,
                                   template_schema,
                                   def_index,
                                   actions):

        for action in actions:
            result = \
                cls._validate_scenario_action(template_schema,
                                              def_index,
                                              action[TemplateFields.ACTION])
            if not result.is_valid_config:
                return result

        return get_content_correct_result()

    @staticmethod
    def _validate_scenario_action(template_schema, def_index, action):
        action_type = action[TemplateFields.ACTION_TYPE]
        action_validator = template_schema.validators.get(action_type)

        if not action_validator:
            LOG.error('%s status code: %s' % (status_msgs[120], 120))
            return get_content_fault_result(120)

        return action_validator.validate(action, def_index)
