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

from oslo_log import log as logging

from vitrage.common.exception import VitrageError

LOG = logging.getLogger(__name__)

operators = [
    '<',
    '<=',
    # '=',
    '==',
    '!=',
    '>=',
    '>',
]

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
        expression = _create_query_expression(query=query_dict)
        LOG.debug('create_predicate::%s', expression)
        expression = 'lambda item: ' + expression
        return eval(expression)
    except Exception as e:
        LOG.error('invalid query format %s. Exception: %s',
                  query_dict, e)
        raise VitrageError('invalid query format %s. Exception: %s',
                           query_dict, e)


def _create_query_expression(query, parent_operator=None):
    expressions = []

    # First element or element under logical operation
    if not parent_operator and isinstance(query, dict):
        (key, value) = query.copy().popitem()
        return _create_query_expression(value, key)

    # Continue recursion on logical (and/or) operation
    elif parent_operator in logical_operations and isinstance(query, list):
        for val in query:
            expressions.append(_create_query_expression(val))
        return _join_logical_operator(parent_operator, expressions)

    # Recursion evaluate leaf (stop condition)
    elif parent_operator in operators:
        for key, val in query.items():
            expressions.append('item.get(' + _evaluable_str(key) + ')' +
                               parent_operator + ' ' + _evaluable_str(val))
        return _join_logical_operator('and', expressions)
    else:
        raise VitrageError('invalid partial query format',
                           parent_operator, query)


def _evaluable_str(value):
    """wrap string/unicode with back tick"""
    if isinstance(value, str):
        return '\'' + value + '\''
    else:
        return str(value)


def _join_logical_operator(op, expressions):
    """Create an expressions string

    Example input:
        op='AND'
        expressions=['a == b', 'c < d']
    Example output: (a == b AND c < d)
    """
    separator = ' ' + op + ' '
    return '(' + separator.join(expressions) + ')'
