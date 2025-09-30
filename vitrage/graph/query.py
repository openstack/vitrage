# Copyright 2016 - Alcatel-Lucent
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

import operator
from oslo_log import log as logging

from vitrage.common.exception import VitrageError

LOG = logging.getLogger(__name__)

operators = [
    '<',
    '<=',
    '==',
    '!=',
    '>=',
    '>',
]

ops = {
    '<': operator.lt,
    '<=': operator.le,
    '==': operator.eq,
    '!=': operator.ne,
    '>=': operator.ge,
    '>': operator.gt,
}

logical_operations = [
    'and',
    'or'
]


def create_predicate(query_dict):
    """Create predicate from a logical and/or/==/>/etc expression

    Example Input:
    --------------
    query_dict = {
        'and': [
            {'==': {'CATEGORY': 'ALARM'}},
            {'or': [
                {'>': {'TIME': 150}},
                {'==': {'VITRAGE_IS_DELETED': True}}
            ]}
        ]
    }

    Example Output:
    --------------
    lambda item: ((item['CATEGORY']== 'ALARM') and
                  ((item['TIME']> 150) or (item['VITRAGE_IS_DELETED']== True)))

    Example Usage:
    --------------
    match = create_predicate(query_dict)
    if match(vertex):
        print vertex

    :param query_dict:
    :return: a predicate "match(item)"
    """
    try:
        return _create_query_function(query=query_dict)
    except Exception as e:
        LOG.error('invalid query format %s. Exception: %s',
                  query_dict, e)
        raise VitrageError('invalid query format %s. Exception: %s',
                           query_dict, e)


def _create_query_function(query, parent_operator=None):

    # First element or element under logical operation
    if not parent_operator and isinstance(query, dict):
        (key, value) = query.copy().popitem()
        return _create_query_function(value, key)

    # Continue recursion on logical (and/or) operation
    elif parent_operator in logical_operations and isinstance(query, list):
        predicates = [_create_query_function(val) for val in query]

        if not predicates:
            return lambda item: False

        if parent_operator == 'and':
            return lambda item: all(p(item) for p in predicates)
        elif parent_operator == 'or':
            return lambda item: any(p(item) for p in predicates)

    # Recursion evaluate leaf (stop condition)
    elif parent_operator in operators:
        predicates = []
        op_func = ops[parent_operator]
        for field, value in query.items():
            predicates.append(
                lambda item, f=field, v=value: op_func(item.get(f), v)
            )

        # Multiple conditions under a comparison operator are implicitly 'and'
        if len(predicates) > 1:
            return lambda item: all(p(item) for p in predicates)
        elif predicates:
            return predicates[0]
        else:
            return lambda item: False

    else:
        raise VitrageError('invalid partial query format',
                           parent_operator, query)
