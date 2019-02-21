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

from vitrage.evaluator.template_fields import TemplateFields
from vitrage.evaluator.template_functions.v2.functions import get_param
from vitrage.evaluator.template_validation.base import ValidationError
from vitrage.evaluator.template_validation.content.v2.get_param_validator \
    import GetParamValidator
from vitrage.tests.unit.evaluator.template_validation.content.base import \
    ValidatorTest


class ParametersValidatorTest(ValidatorTest):

    def test_validate_no_parameters(self):
        template = {'no parameters in this template': 'at all'}
        result = \
            GetParamValidator.validate(template=template, actual_params={})
        self._assert_correct_result(result)

    def test_validate_empty_parameters(self):
        template = {'parameters': ''}
        result = \
            GetParamValidator.validate(template=template, actual_params={})
        self._assert_correct_result(result)

    def test_validate_single_parameter(self):
        template = {
            'parameters': {
                'single_param': {
                    TemplateFields.DESCRIPTION: 'blabla',
                    TemplateFields.DEFAULT: 'this is my default'
                }
            }
        }
        result = \
            GetParamValidator.validate(template=template, actual_params={})
        self._assert_correct_result(result)

    def test_validate_few_parameters(self):
        template = {
            'parameters': {
                'param1': {
                    TemplateFields.DESCRIPTION: 'blabla',
                    TemplateFields.DEFAULT: 'this is my default'
                },
                'param2': {
                    TemplateFields.DESCRIPTION: 'blabla2',
                },
                'param3': {
                    TemplateFields.DEFAULT: 'this is my default3'
                },
                'param4': {
                },
            }
        }
        result = \
            GetParamValidator.validate(template=template, actual_params={})
        self._assert_correct_result(result)

    def test_validate_get_param_with_no_parameters(self):
        template = {'alarm_name': 'get_param(param1)'}
        self.assert_get_param_result('get_param(param1)',
                                     template,
                                     expected_error_code=161)

    def test_validate_get_param_with_empty_parameters(self):
        template = {}
        self.assert_get_param_result('get_param(param1)',
                                     template,
                                     expected_error_code=161)

    def test_validate_get_param_with_undefined_parameter(self):
        template = {
            'parameters': {
                'param1': {
                    TemplateFields.DESCRIPTION: 'blabla',
                    TemplateFields.DEFAULT: 'this is my default'
                },
                'param2': {
                    TemplateFields.DESCRIPTION: 'blabla2',
                },
            }
        }
        self.assert_get_param_result('get_param(undefined)',
                                     template,
                                     expected_error_code=161)

    def test_validate_get_param_with_valid_parameter(self):
        template = {
            'parameters': {
                'param1': {
                    TemplateFields.DESCRIPTION: 'blabla',
                    TemplateFields.DEFAULT: 'this is my default'
                },
                'param2': {
                    TemplateFields.DESCRIPTION: 'blabla2',
                },
            }
        }
        self.assert_get_param_result('get_param(param1)',
                                     template,
                                     expected_error_code=0)

    def test_validate_get_param_with_malformed_parameter(self):
        template = {
            'parameters': {
                'param1': {
                    TemplateFields.DESCRIPTION: 'blabla',
                    TemplateFields.DEFAULT: 'this is my default'
                },
                'param2': {
                    TemplateFields.DESCRIPTION: 'blabla2',
                },
            }
        }

        self.assert_get_param_result(
            'get_param(param1', template, expected_error_code=162)

        self.assert_get_param_result(
            'get_paramparam1)', template, expected_error_code=162)

        self.assert_get_param_result(
            'get_paramparam1', template, expected_error_code=162)

        self.assert_get_param_result(
            'get_param', template, expected_error_code=162)

        self.assert_get_param_result(
            'get_param()', template, expected_error_code=162)

        self.assert_get_param_result(
            'get_param)param1(', template, expected_error_code=162)

    def test_validate_get_param_with_actual_parameter(self):
        template = {
            'parameters': {
                'param1': {
                    TemplateFields.DESCRIPTION: 'blabla',
                    TemplateFields.DEFAULT: 'this is my default'
                },
                'param2': {
                    TemplateFields.DESCRIPTION: 'blabla2',
                },
            }
        }
        actual_params = {
            'param1': 'value1',
            'param2': 'value2'
        }
        self.assert_get_param_result('get_param(param2)',
                                     template,
                                     actual_params,
                                     expected_result='value2')

    def test_validate_get_param_with_missing_actual_parameter(self):
        template = {
            'parameters': {
                'param1': {
                    TemplateFields.DESCRIPTION: 'blabla',
                    TemplateFields.DEFAULT: 'this is my default'
                },
                'param2': {
                    TemplateFields.DESCRIPTION: 'blabla2',
                },
            }
        }
        actual_params = {
            'param1': 'value1',
        }
        self.assert_get_param_result('get_param(param2)',
                                     template, actual_params,
                                     expected_error_code=163)

    def test_validate_get_param_with_default_actual_parameter(self):
        template = {
            'parameters': {
                'param1': {
                    TemplateFields.DESCRIPTION: 'blabla',
                    TemplateFields.DEFAULT: 'this is my default'
                },
                'param2': {
                    TemplateFields.DESCRIPTION: 'blabla2',
                },
            }
        }
        actual_params = {
            'param2': 'value2',
        }
        self.assert_get_param_result('get_param(param1)',
                                     template,
                                     actual_params,
                                     expected_result='this is my default')

    def assert_get_param_result(self,
                                func_str,
                                template,
                                actual_params=None,
                                expected_result=None,
                                expected_error_code=None):
        error = None
        try:
            result = get_param(func_str, template, actual_params=actual_params)
        except ValidationError as e:
            error = e

        if expected_error_code:
            self.assertIsNotNone(error)
            self.assertEqual(error.code, expected_error_code)
        else:
            self.assertIsNone(error)
            if expected_result:
                self.assertEqual(expected_result, result)
