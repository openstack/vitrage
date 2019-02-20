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
from vitrage.tests.functional.api_handler.test_templates import TestTemplates

TEMPLATE_WITH_PARAMS = 'v3_with_params.yaml'
TEMPLATE_WITH_EXTRA_PARAM_DEF = 'v3_with_extra_param_def.yaml'
TEMPLATE_WITH_MISSING_PARAM_DEF = 'v3_with_missing_param_def.yaml'


class TestTemplatesV3(TestTemplates):

    def test_validate_template_with_no_params(self):
        self._validate_template_with_no_params(TEMPLATE_WITH_PARAMS)

    def test_validate_template_with_missing_param(self):
        self._validate_template_with_missing_param(TEMPLATE_WITH_PARAMS)

    def test_validate_template_with_actual_params(self):
        self._validate_template_with_actual_params(TEMPLATE_WITH_PARAMS)

    def test_validate_template_with_missing_param_def(self):
        self._validate_template_with_missing_param_def(
            TEMPLATE_WITH_MISSING_PARAM_DEF)

    def test_validate_template_with_extra_actual_param(self):
        self._validate_template_with_extra_actual_param(TEMPLATE_WITH_PARAMS)

    def test_validate_template_with_extra_param_def(self):
        self._validate_template_with_extra_param_def(
            TEMPLATE_WITH_EXTRA_PARAM_DEF)

    def test_add_template_with_no_params(self):
        self._add_template_with_no_params(TEMPLATE_WITH_PARAMS)

    def test_add_template_with_missing_param(self):
        self._add_template_with_missing_param(TEMPLATE_WITH_PARAMS)

    def test_add_template_with_actual_params(self):
        self._add_template_with_actual_params(TEMPLATE_WITH_PARAMS)

    def test_add_template_with_missing_param_def(self):
        self._add_template_with_missing_param_def(
            TEMPLATE_WITH_MISSING_PARAM_DEF)

    def test_add_template_with_extra_actual_param(self):
        self._add_template_with_extra_actual_param(TEMPLATE_WITH_PARAMS)

    def test_add_template_with_extra_param_def(self):
        self._add_template_with_extra_param_def(TEMPLATE_WITH_EXTRA_PARAM_DEF)
