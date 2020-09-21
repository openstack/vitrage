# Copyright 2019 - Nokia
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

from collections import namedtuple
from oslo_log import log
import re

from vitrage.evaluator.template_validation.base import ValidationError

LOG = log.getLogger(__name__)

FuncInfo = namedtuple('FuncInfo', ['name', 'func', 'error_code'])


def resolve_function(func_info, template, **kwargs):
    return _traverse_function(func_info, template, resolve=True, **kwargs)


def validate_function(func_info, template, **kwargs):
    return _traverse_function(func_info, template, resolve=False, **kwargs)


def _traverse_function(func_info, template, resolve, **kwargs):
    return _recursive_resolve_function(
        func_info, template, template, resolve, **kwargs)


def _recursive_resolve_function(func_info, template, template_block,
                                resolve, **kwargs):

    for key, value in template_block.items():
        if isinstance(value, str) and \
                _is_wanted_function(value, func_info.name):

            if not func_info.func:
                raise ValidationError(func_info.error_code, value)

            resolved_value = func_info.func(value, template, **kwargs)
            if resolve:
                template_block[key] = resolved_value
                LOG.debug('Replaced %s with %s', value, resolved_value)

        elif isinstance(value, dict):
            _recursive_resolve_function(
                func_info, template, value, resolve, **kwargs)

        elif isinstance(value, list):
            for item in value:
                _recursive_resolve_function(
                    func_info, template, item, resolve, **kwargs)


def is_function(str):
    """Check if the string represents a function

    A function has the format: func_name(params)
    Search for a regex with open and close parenthesis
    """
    return re.match(r'.*\(.*\)', str)


def _is_wanted_function(str, func_name):
    """Check if the string represents `func_name` function

    A function has the format: func_name(params)
    Search for a regex with open and close parenthesis
    """
    return re.match(func_name + r'\(.*\)', str)
