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

from vitrage.evaluator.template_validation.content.v1.get_param_validator \
    import GetParamValidator
from vitrage.tests.unit.evaluator.template_validation.content.base import \
    ValidatorTest


class ParametersValidatorTest(ValidatorTest):
    """Tests for the parameters validator of version 1

       All tests should succeed, as long as there is no get_param reference in
       the template itself
    """

    def test_validate_no_parameters(self):
        result = GetParamValidator.validate(
            template={'alarm_name': "Don't add a comment"}, actual_params=None)
        self._assert_correct_result(result)

    def test_validate_empty_parameters(self):
        result = GetParamValidator.validate(
            template={'alarm_name': '+2 for everybody'}, actual_params={})
        self._assert_correct_result(result)

    def test_validate_with_parameter(self):
        template = {'alarm_name': 'get_param(param1)'}
        result = \
            GetParamValidator.validate(template=template, actual_params={})
        self._assert_fault_result(result, 160)
