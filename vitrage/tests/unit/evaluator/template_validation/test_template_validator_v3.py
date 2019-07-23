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

import json

from vitrage.api_handler.apis.template import TemplateApis
from vitrage.evaluator.actions.recipes import execute_mistral
from vitrage.evaluator.template_fields import TemplateFields as TF
from vitrage.tests import base
from vitrage.tests.functional.test_configuration import TestConfiguration
from vitrage.tests.mocks.utils import get_resources_dir
from vitrage.utils import file as file_utils


class TemplateValidatorV3Test(base.BaseTest, TestConfiguration):

    def setUp(self):
        super(TemplateValidatorV3Test, self).setUp()
        self.add_db()
        self.template_apis = TemplateApis(db=self._db)

    def _test_validation(self, file=None, content=None, expected_code=0):
        if file and not content:
            content = self._get_yaml(file)
        self._call_validate_api('/tmp/tmp', content, expected_code)

    @staticmethod
    def _get_yaml(filename):
        path = '%s/templates/v3_templates/%s' % (get_resources_dir(), filename)
        return file_utils.load_yaml_file(path)

    def _call_validate_api(self, path, content, expected_error_code):
        templates = [[
            path,
            content,
        ]]
        results = self.template_apis.validate_template(None, templates, None)
        result = json.loads(results)['results'][0]
        self.assertEqual(expected_error_code, result['status code'],
                         message='GOT ' + result['message'])

    def test_actions(self):
        template = self._get_yaml('valid_actions.yaml')
        self._test_validation(content=template, expected_code=0)

        del template[TF.SCENARIOS][0][TF.CONDITION]
        self._test_validation(content=template, expected_code=83)

        del template[TF.SCENARIOS][0]
        del template[TF.SCENARIOS][0][TF.ACTIONS]
        self._test_validation(content=template, expected_code=84)

    def test_set_state(self):
        template = self._get_yaml('valid_actions.yaml')

        valid_action = {
            'set_state': {
                TF.TARGET: 'host',
                TF.STATE: 'BAD',
            }
        }
        template[TF.SCENARIOS][0][TF.ACTIONS].append(valid_action)
        self._test_validation(content=template, expected_code=0)

        valid_action['set_state'] = {
            TF.TARGET: 'host_incorrect_key',
            TF.STATE: 'BAD',
        }
        self._test_validation(content=template, expected_code=10101)

        valid_action['set_state'] = {
            TF.STATE: 'BAD',
        }
        self._test_validation(content=template, expected_code=10100)

        valid_action['set_state'] = {
            TF.TARGET: 'host',
            TF.STATE: 'BAD',
            'kuku': 'kuku',
        }
        self._test_validation(content=template, expected_code=4)

        valid_action['set_state'] = {
            TF.TARGET: 'host',
        }
        self._test_validation(content=template, expected_code=128)

    def test_mark_down(self):
        template = self._get_yaml('valid_actions.yaml')

        valid_action = {
            'mark_down': {
                TF.TARGET: 'host',
            }
        }
        template[TF.SCENARIOS][0][TF.ACTIONS].append(valid_action)
        self._test_validation(content=template, expected_code=0)

        valid_action['mark_down'] = {
            TF.TARGET: 'host_incorrect_key',
        }
        self._test_validation(content=template, expected_code=10101)

        valid_action['mark_down'] = {}
        self._test_validation(content=template, expected_code=10100)

        valid_action['mark_down'] = {
            TF.TARGET: 'host',
            'kuku': 'kuku',
        }
        self._test_validation(content=template, expected_code=4)

    def test_raise_alarm(self):
        self._test_validation(file='valid_actions.yaml', expected_code=0)
        template = self._get_yaml('valid_actions.yaml')

        valid_action = {
            'raise_alarm': {
                TF.TARGET: 'host',
                TF.ALARM_NAME: 'BAD',
                TF.SEVERITY: 'BAD',
            }
        }
        template[TF.SCENARIOS][0][TF.ACTIONS].append(valid_action)
        self._test_validation(content=template, expected_code=0)

        valid_action['raise_alarm'] = {
            TF.TARGET: 'host_incorrect_key',
            TF.ALARM_NAME: 'BAD',
            TF.SEVERITY: 'BAD',
        }
        self._test_validation(content=template, expected_code=10101)

        valid_action['raise_alarm'] = {
            TF.TARGET: 'host',
            TF.ALARM_NAME: 'BAD',
            TF.SEVERITY: 'BAD',
            'kuku': 'kuku',
        }
        self._test_validation(content=template, expected_code=4)

        valid_action['raise_alarm'] = {
            TF.ALARM_NAME: 'BAD',
            TF.SEVERITY: 'BAD',
        }
        self._test_validation(content=template, expected_code=10100)

        valid_action['raise_alarm'] = {
            TF.TARGET: 'host',
            TF.SEVERITY: 'BAD',
        }
        self._test_validation(content=template, expected_code=10104)

        valid_action['raise_alarm'] = {
            TF.TARGET: 'host',
            TF.ALARM_NAME: 'BAD',
        }
        self._test_validation(content=template, expected_code=126)

        valid_action['raise_alarm'] = {
            TF.TARGET: 'host',
            TF.ALARM_NAME: 'BAD',
            TF.SEVERITY: 'BAD',
            TF.CAUSING_ALARM: 'host_ssh_alarm'
        }
        self._test_validation(content=template, expected_code=0)

        valid_action['raise_alarm'] = {
            TF.TARGET: 'host',
            TF.ALARM_NAME: 'BAD',
            TF.SEVERITY: 'BAD',
            TF.CAUSING_ALARM: 'host_ssh_alarm_incorrect_key'
        }
        self._test_validation(content=template, expected_code=10107)

    def test_add_causal_relationship(self):
        self._test_validation(file='valid_actions.yaml', expected_code=0)
        template = self._get_yaml('valid_actions.yaml')

        valid_action = {
            'add_causal_relationship': {
                TF.TARGET: 'host_ssh_alarm',
                TF.SOURCE: 'host_network_alarm',
            }
        }
        template[TF.SCENARIOS][0][TF.ACTIONS].append(valid_action)
        self._test_validation(content=template, expected_code=0)

        valid_action['add_causal_relationship'] = {
            TF.TARGET: 'host_ssh_alarm_incorrect_key',
            TF.SOURCE: 'host_network_alarm',
        }
        self._test_validation(content=template, expected_code=10101)

        valid_action['add_causal_relationship'] = {
            TF.TARGET: 'host_ssh_alarm',
            TF.SOURCE: 'host_network_alarm_incorrect_key',
        }
        self._test_validation(content=template, expected_code=10103)

        valid_action['add_causal_relationship'] = {
            TF.SOURCE: 'host_network_alarm',
        }
        self._test_validation(content=template, expected_code=10100)

        valid_action['add_causal_relationship'] = {
            TF.TARGET: 'host_ssh_alarm',
        }
        self._test_validation(content=template, expected_code=10102)

    def test_execute_mistral(self):
        template = self._get_yaml('valid_actions.yaml')

        valid_action = {
            'execute_mistral': {
                execute_mistral.WORKFLOW: 'kuku',
                execute_mistral.INPUT: {},
            }
        }

        template[TF.SCENARIOS][0][TF.ACTIONS].append(valid_action)
        self._test_validation(content=template, expected_code=0)

        valid_action['execute_mistral'] = {
            execute_mistral.WORKFLOW: {},
            execute_mistral.INPUT: {},
        }
        self._test_validation(content=template, expected_code=4)

        valid_action['execute_mistral'] = {execute_mistral.INPUT: {}}
        self._test_validation(content=template, expected_code=10105)

        valid_action['execute_mistral'] = {execute_mistral.WORKFLOW: 'kuku'}
        self._test_validation(content=template, expected_code=0)

        valid_action['execute_mistral'] = {
            execute_mistral.WORKFLOW: 'kuku',
            execute_mistral.INPUT: {'kuku': 'get_attr('}
        }
        self._test_validation(content=template, expected_code=138)

        valid_action['execute_mistral'] = {
            execute_mistral.WORKFLOW: 'kuku',
            execute_mistral.INPUT: {'kuku': 'get_attr(host, name)'},
        }
        self._test_validation(content=template, expected_code=0)

    def test_conditions(self):
        self._test_validation(file='valid_conditions.yaml', expected_code=0)
        template = self._get_yaml('valid_conditions.yaml')

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'host AND NOT host host [contains] instance'
        self._test_validation(content=template, expected_code=85)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'host AND instance host [contains] instance'
        self._test_validation(content=template, expected_code=85)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'host AND NOT host [host contains] instance'
        self._test_validation(content=template, expected_code=85)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'host AND instance host [contains] instance'
        self._test_validation(content=template, expected_code=85)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'NOT host [contains] instance'
        self._test_validation(content=template, expected_code=134)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'NOT host [contains] instance AND NOT host [contains] instance'
        self._test_validation(content=template, expected_code=134)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'NOT (host [ contains ] instance or host [ contains ] instance)'
        self._test_validation(content=template, expected_code=134)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'NOT host_incorrect_key'
        self._test_validation(content=template, expected_code=10200)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'host_incorrect_key'
        self._test_validation(content=template, expected_code=10200)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'host [contains] instance_incorrect_key'
        self._test_validation(content=template, expected_code=10200)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'host_incorrect_key [contains] instance'
        self._test_validation(content=template, expected_code=10200)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'NOT host'
        self._test_validation(content=template, expected_code=86)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            '(host_incorrect_key)'
        self._test_validation(content=template, expected_code=10200)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            '(  host OR host [contains] instance  ) AND' \
            ' (instance OR host [contains] instance'  # missing parentheses
        self._test_validation(content=template, expected_code=85)

        template[TF.SCENARIOS][0][TF.CONDITION] = 'host OR instance'
        self._test_validation(content=template, expected_code=135)

        template[TF.SCENARIOS][0][TF.CONDITION] = \
            'host OR NOT host [contains] instance'
        self._test_validation(content=template, expected_code=135)

    def test_regex(self):
        template = self._get_yaml('valid_actions.yaml')
        template[TF.ENTITIES]['entity_regex'] = {'name.regex': 'bad.regex('}
        self._test_validation(content=template, expected_code=47)

    def test_basic(self):
        template = self._get_yaml('valid_conditions.yaml')
        del template[TF.SCENARIOS]
        self._test_validation(content=template, expected_code=80)

        template = self._get_yaml('valid_conditions.yaml')
        del template[TF.ENTITIES]
        self._test_validation(content=template, expected_code=10101)

        template = self._get_yaml('valid_conditions.yaml')
        template['kuku'] = {}
        self._test_validation(content=template, expected_code=4)
