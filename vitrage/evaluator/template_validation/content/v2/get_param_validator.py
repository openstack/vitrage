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

from vitrage.evaluator.template_functions import function_resolver
from vitrage.evaluator.template_functions import GET_PARAM
from vitrage.evaluator.template_functions.v2.functions import get_param
from vitrage.evaluator.template_validation.base import get_custom_fault_result
from vitrage.evaluator.template_validation.base import ValidationError
from vitrage.evaluator.template_validation.content.base import \
    get_content_correct_result


class GetParamValidator(object):

    @classmethod
    def validate(cls, template, actual_params):
        try:
            function_resolver.validate_function(
                function_resolver.FuncInfo(
                    name=GET_PARAM, func=get_param, error_code=0),
                template,
                actual_params=actual_params)
        except ValidationError as e:
            return get_custom_fault_result(e.code, e.details)
        return get_content_correct_result()
