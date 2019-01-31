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

import abc
from collections import namedtuple
from sympy.logic.boolalg import And
from sympy.logic.boolalg import Not
from sympy.logic.boolalg import Or
from sympy.logic.boolalg import to_dnf as sympy_to_dnf
from sympy import Symbol


ConditionVar = namedtuple('ConditionVar', ['symbol_name', 'positive'])


class SymbolResolver(object):
    @abc.abstractmethod
    def is_relationship(self, symbol):
        pass

    @abc.abstractmethod
    def get_relationship_source_id(self, relationship):
        pass

    @abc.abstractmethod
    def get_relationship_target_id(self, relationship):
        pass

    @abc.abstractmethod
    def get_entity_id(self, entity):
        pass


def get_condition_common_targets(condition,
                                 definitions_index,
                                 symbol_resolver):
    """Return the targets that are common to all clauses of the condition.

    Common targets include:
       * And condition - any vertex that is part of the condition can
                         be a target
       * Not condition - no vertex that is part of the condition can
                         be a target
       * Or condition - vertices that appear in any "positive" part (i.e. one
                        that doesn't have a 'not' in front of it) of the
                        Or condition

    A complete description of all options can be found in Vitrage
    'external-actions' spec.

    The condition format:
        [[and_var1, and_var2, ...], or_list_2, ...]

    :return: A set of vertices that are common to all clauses of the condition
    """

    clauses_targets = []

    for clause in condition:
        clause_targets = set()

        for term in clause:
            if term.positive:
                symbol = definitions_index.get(term.symbol_name)
                if symbol and symbol_resolver.is_relationship(symbol):
                    clause_targets.add(
                        symbol_resolver.get_relationship_source_id(symbol))
                    clause_targets.add(
                        symbol_resolver.get_relationship_target_id(symbol))
                elif symbol:
                    clause_targets.add(symbol_resolver.get_entity_id(symbol))

        clauses_targets.append(clause_targets)

    return set.intersection(*clauses_targets)


def is_condition_include_positive_clause(condition):
    """Check if a condition is positive

    A positive condition has at least one part that is not 'not'

    Positive conditions:
        host_contains_instance
        host and not host_contains_instance

    Negative conditions:
        not host_contains_instance
        not host_contains_instance or not alarm_on_host

    The condition format:
        [[and_var1, and_var2, ...], or_list_2, ...]

    :return: True if the condition is positive
    """
    is_positive = False

    for clause in condition:
        for term in clause:
            if term.positive:
                is_positive = True

    return is_positive


def parse_condition(condition_str):
    """Parse condition string into an object

    The condition string will be converted here into DNF (Disjunctive
    Normal Form), e.g., (X and Y) or (X and Z) or (X and V and not W)
    ... where X, Y, Z, V, W are either entities or relationships
    more details: https://en.wikipedia.org/wiki/Disjunctive_normal_form

    The condition variable lists is then extracted from the DNF object.
    It is a list of lists. Each inner list represents an AND expression
    compound condition variables. The outer list presents the OR
    expression

      [[and_var1, and_var2, ...], or_list_2, ...]

    :param condition_str: the string as it written in the template
    :return: condition_vars_lists
    """

    condition_dnf = convert_to_dnf_format(condition_str)

    if isinstance(condition_dnf, Or):
        return extract_or_condition(condition_dnf)

    if isinstance(condition_dnf, And):
        return [extract_and_condition(condition_dnf)]

    if isinstance(condition_dnf, Not):
        return [(extract_not_condition_var(condition_dnf))]

    if isinstance(condition_dnf, Symbol):
        return [[(extract_condition_var(condition_dnf, True))]]


def convert_to_dnf_format(condition_str):
    condition_str = condition_str.replace(' and ', '&')
    condition_str = condition_str.replace(' AND ', '&')
    condition_str = condition_str.replace(' or ', '|')
    condition_str = condition_str.replace(' OR ', '|')
    condition_str = condition_str.replace(' not ', '~')
    condition_str = condition_str.replace(' NOT ', '~')
    condition_str = condition_str.replace('not ', '~')
    condition_str = condition_str.replace('NOT ', '~')

    return sympy_to_dnf(condition_str)


def extract_or_condition(or_condition):

    vars_ = []
    for var in or_condition.args:

        if isinstance(var, And):
            vars_.append(extract_and_condition(var))
        else:
            is_symbol = isinstance(var, Symbol)
            vars_.append([extract_condition_var(var, is_symbol)])

    return vars_


def extract_and_condition(and_condition):
    return [extract_condition_var(arg, isinstance(arg, Symbol))
            for arg in and_condition.args]


def extract_not_condition_var(not_condition):
    return [extract_condition_var(arg, False)
            for arg in not_condition.args]


def extract_condition_var(symbol, positive):
    if isinstance(symbol, Not):
        return extract_not_condition_var(symbol)[0]
    return ConditionVar(symbol.name, positive)
