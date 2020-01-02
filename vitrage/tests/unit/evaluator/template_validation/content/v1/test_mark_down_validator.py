# Copyright 2017 - Nokia
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

from vitrage.evaluator.actions.base import ActionType
from vitrage.evaluator.template_fields import TemplateFields
from vitrage.evaluator.template_validation.content.v1.mark_down_validator \
    import MarkDownValidator
from vitrage.tests.unit.evaluator.template_validation.content.base import \
    ActionValidatorTest


class MarkDownValidatorTest(ActionValidatorTest):
    def test_validate_mark_down_action(self):

        self._validate_action(self._create_mark_down_action('123'),
                              MarkDownValidator.validate)

    def test_validate_mark_down_action_without_action_target(self):

        self._validate_action_without_action_target(
            self._create_mark_down_action('123'),
            MarkDownValidator.validate
        )

    def test_validate_mark_down_action_with_invalid_target_id(self):

        self._validate_action_with_invalid_target_id(
            self._create_mark_down_action('unknown'),
            MarkDownValidator.validate
        )

    def test_validate_mark_down_action_without_target_id(self):

        self._validate_action_without_target_id(
            self._create_mark_down_action('123'),
            MarkDownValidator.validate,
            131
        )

    @staticmethod
    def _create_mark_down_action(target):

        action_target = {
            TemplateFields.TARGET: target
        }
        action = {
            TemplateFields.ACTION_TYPE: ActionType.MARK_DOWN,
            TemplateFields.ACTION_TARGET: action_target,
        }
        return action
