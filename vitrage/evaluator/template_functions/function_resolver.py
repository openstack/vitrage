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
import six

from vitrage.evaluator.template_validation.content.base import \
    get_content_correct_result
from vitrage.evaluator.template_validation.content.base import \
    get_content_fault_result
from vitrage.evaluator.template_validation.status_messages import status_msgs

LOG = log.getLogger(__name__)

FuncInfo = namedtuple('FuncInfo', ['name', 'func', 'error_code'])


class FunctionResolver(object):
    @classmethod
    def resolve_function(cls, func_info, template, **kwargs):
        return cls._traverse_function(func_info, template, True, **kwargs)

    @classmethod
    def validate_function(cls, func_info, template, **kwargs):
        return cls._traverse_function(func_info, template, False, **kwargs)

    @classmethod
    def _traverse_function(cls, func_info, template, resolve, **kwargs):
        return cls._recursive_resolve_function(
            func_info, template, template, resolve, **kwargs)

    @classmethod
    def _recursive_resolve_function(cls, func_info, template, template_block,
                                    resolve, **kwargs):
        result = get_content_correct_result()

        for key, value in template_block.items():
            if result.is_valid_config:
                if isinstance(value, six.string_types) and \
                        _is_wanted_function(value, func_info.name):

                    func = func_info.func
                    if not func:
                        status = func_info.error_code
                        LOG.error('%s status code: %s' %
                                  (status_msgs[status], status))
                        return get_content_fault_result(status)

                    result, resolved_value = func(value, template, **kwargs)
                    if result.is_valid_config and resolve:
                        template_block[key] = resolved_value
                        LOG.debug('Replaced %s with %s', value,
                                  resolved_value)

                elif isinstance(value, dict):
                    result = cls._recursive_resolve_function(
                        func_info, template, value, resolve, **kwargs)

                elif isinstance(value, list):
                    for item in value:
                        if result.is_valid_config:
                            result = cls._recursive_resolve_function(
                                func_info, template, item, resolve, **kwargs)

        return result


def is_function(str):
    """Check if the string represents a function

    A function has the format: func_name(params)
    Search for a regex with open and close parenthesis
    """
    return re.match('.*\(.*\)', str)


def _is_wanted_function(str, func_name):
    """Check if the string represents `func_name` function

    A function has the format: func_name(params)
    Search for a regex with open and close parenthesis
    """
    return re.match(func_name + '\(.*\)', str)
