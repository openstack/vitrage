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
from collections import namedtuple
from vitrage.evaluator.template_validation.status_messages import status_msgs
RESULT_DESCRIPTION = 'Template syntax validation'
EXCEPTION = 'exception'

Result = namedtuple('Result', ['description', 'is_valid_config', 'status_code',
                               'comment'])


class ValidationError(Exception):
    def __init__(self, code, *args):
        self.code = code
        self.details = ''
        self.details = ','.join(str(arg) for arg in args)


def get_correct_result(description=RESULT_DESCRIPTION):
    return Result(description, True, 0, status_msgs[0])


def get_warning_result(description, code):
    return Result(description, True, code, status_msgs[code])


def get_fault_result(description, code, msg=None):
    if msg:
        return Result(description, False, code, msg)
    return Result(description, False, code, status_msgs[code])


def get_custom_fault_result(code, msg):
    return Result('Template validation', False, code,
                  status_msgs[code] + ' - ' + msg)


def get_status_code(voluptuous_error):
    prefix = str(voluptuous_error).split(' ')[0].strip()
    if prefix.isdigit():
        return int(prefix)
    return 4
