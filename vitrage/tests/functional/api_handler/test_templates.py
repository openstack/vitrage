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
from oslo_config import cfg
from testtools import matchers

from vitrage.api_handler.apis.template import TemplateApis
from vitrage.tests.functional.test_configuration import TestConfiguration
from vitrage.tests.mocks import utils
from vitrage.tests.unit.entity_graph.base import TestEntityGraphUnitBase


class TestTemplates(TestEntityGraphUnitBase, TestConfiguration):
    TEMPLATE_WITH_PARAMS = 'with_params.yaml'
    TEMPLATE_WITH_EXTRA_PARAM_DEF = 'with_extra_param_def.yaml'
    TEMPLATE_WITH_MISSING_PARAM_DEF = 'with_missing_param_def.yaml'
    TEMPLATE_WITHOUT_PARAMS = 'without_params.yaml'
    VALIDATION_FAILED = 'validation failed'
    VALIDATION_OK = 'validation OK'

    class MockNotifier(object):
        def notify(self, event_type, data):
            pass

    @classmethod
    def setUpClass(cls):
        super(TestTemplates, cls).setUpClass()
        cls.conf = cfg.ConfigOpts()
        cls.add_db(cls.conf)
        cls.apis = TemplateApis(notifier=cls.MockNotifier(), db=cls._db)
        cls.added_template = None

    def tearDown(self):
        super(TestTemplates, self).tearDown()
        self._delete_templates()

    def test_validate_template_with_no_params(self):
        # Setup
        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_PARAMS)
        files_content = [(template_path, self._load_yaml_file(template_path))]

        # Action
        results = self.apis.validate_template(
            ctx=None, templates=files_content, template_type=None, params=None)

        # Test assertions
        self._assert_validate_template_result(
            self.VALIDATION_FAILED, 163,
            'Failed to resolve parameter', results)

    def test_validate_template_with_missing_param(self):
        # Setup
        apis = TemplateApis(notifier=self.MockNotifier(), db=self._db)

        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_PARAMS)
        files_content = [(template_path, self._load_yaml_file(template_path))]
        params = {'template_name': 'template_with_params_1',
                  'alarm_name': 'My alarm', 'new_state': 'SUBOPTIMAL'}

        # Action
        results = apis.validate_template(ctx=None, templates=files_content,
                                         template_type=None, params=params)

        # Test assertions
        self._assert_validate_template_result(
            self.VALIDATION_FAILED, 163,
            'Failed to resolve parameter', results)

    def test_validate_template_with_actual_params(self):
        # Setup
        apis = TemplateApis(notifier=self.MockNotifier(), db=self._db)

        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_PARAMS)
        files_content = [(template_path, self._load_yaml_file(template_path))]
        params = {'template_name': 'template_with_params_2',
                  'alarm_type': 'zabbix', 'alarm_name': 'My alarm',
                  'new_state': 'SUBOPTIMAL'}

        # Action
        results = apis.validate_template(ctx=None, templates=files_content,
                                         template_type=None, params=params)

        # Test assertions
        self._assert_validate_template_result(
            self.VALIDATION_OK, 0, 'Template validation is OK', results)

    def test_validate_template_with_missing_param_def(self):
        # Setup
        apis = TemplateApis(notifier=self.MockNotifier(), db=self._db)

        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_MISSING_PARAM_DEF)
        files_content = [(template_path, self._load_yaml_file(template_path))]
        params = {'alarm_type': 'zabbix', 'alarm_name': 'My alarm',
                  'new_state': 'SUBOPTIMAL'}

        # Action
        results = apis.validate_template(ctx=None, templates=files_content,
                                         template_type=None, params=params)

        # Test assertions
        self._assert_validate_template_result(
            self.VALIDATION_FAILED, 161, 'get_param called for a parameter '
            'that is not defined in the \'parameters\' block', results)

    def test_validate_template_without_params(self):
        # Setup
        apis = TemplateApis(notifier=self.MockNotifier(), db=self._db)

        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITHOUT_PARAMS)
        files_content = [(template_path, self._load_yaml_file(template_path))]

        # Action
        results = apis.validate_template(ctx=None, templates=files_content,
                                         template_type=None, params=None)

        # Test assertions
        self._assert_validate_template_result(
            self.VALIDATION_OK, 0, 'Template validation is OK', results)

    def test_validate_template_with_extra_actual_param(self):
        # Setup
        apis = TemplateApis(notifier=self.MockNotifier(), db=self._db)

        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_PARAMS)
        files_content = [(template_path, self._load_yaml_file(template_path))]
        params = {'template_name': 'template_with_params_2',
                  'alarm_type': 'zabbix', 'alarm_name': 'My alarm',
                  'new_state': 'SUBOPTIMAL',
                  'non_existing_param': 'some value'}

        # Action
        results = apis.validate_template(ctx=None, templates=files_content,
                                         template_type=None, params=params)

        # Test assertions
        self._assert_validate_template_result(
            self.VALIDATION_OK, 0, 'Template validation is OK', results)

    def test_validate_template_with_extra_param_def(self):
        # Setup
        apis = TemplateApis(notifier=self.MockNotifier(), db=self._db)

        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_EXTRA_PARAM_DEF)
        files_content = [(template_path, self._load_yaml_file(template_path))]
        params = {'template_name': 'template_with_params_2',
                  'alarm_type': 'zabbix', 'alarm_name': 'My alarm',
                  'new_state': 'SUBOPTIMAL'}

        # Action
        results = apis.validate_template(ctx=None, templates=files_content,
                                         template_type=None, params=params)

        # Test assertions
        self._assert_validate_template_result(
            self.VALIDATION_OK, 0, 'Template validation is OK', results)

    def test_add_template_with_no_params(self):
        # Setup
        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_PARAMS)
        files_content = [(template_path, self._load_yaml_file(template_path))]

        # Action.
        added_templates = \
            self.apis.add_template(ctx=None, templates=files_content,
                                   template_type=None, params=None)
        self.added_template = added_templates[0]['uuid']

        # Test assertions
        self.assertThat(added_templates, matchers.HasLength(1))
        self.assertEqual('ERROR', added_templates[0]['status'])
        self.assertEqual('Failed to resolve parameter',
                         added_templates[0]['status details'])

    def test_add_template_with_missing_param(self):
        # Setup
        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_PARAMS)
        files_content = [(template_path, self._load_yaml_file(template_path))]
        params = {'template_name': 'template_with_params_3',
                  'alarm_name': 'My alarm', 'new_state': 'SUBOPTIMAL'}

        # Action
        added_templates = \
            self.apis.add_template(ctx=None, templates=files_content,
                                   template_type=None, params=params)
        self.added_template = added_templates[0]['uuid']

        # Test assertions
        self.assertThat(added_templates, matchers.HasLength(1))
        self.assertEqual('ERROR', added_templates[0]['status'])
        self.assertEqual('Failed to resolve parameter',
                         added_templates[0]['status details'])

    def test_add_template_with_actual_params(self):
        # Setup
        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_PARAMS)
        files_content = [(template_path, self._load_yaml_file(template_path))]
        params = {'template_name': 'template_with_params_4',
                  'alarm_type': 'zabbix', 'alarm_name': 'My alarm',
                  'new_state': 'SUBOPTIMAL'}

        # Action
        added_templates = \
            self.apis.add_template(ctx=None, templates=files_content,
                                   template_type=None, params=params)
        self.added_template = added_templates[0]['uuid']

        # Test assertions
        self.assertThat(added_templates, matchers.HasLength(1))
        self.assertEqual('LOADING', added_templates[0]['status'])

    def test_add_template_with_missing_param_def(self):
        # Setup
        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_MISSING_PARAM_DEF)
        files_content = [(template_path, self._load_yaml_file(template_path))]
        params = {'alarm_type': 'zabbix', 'alarm_name': 'My alarm',
                  'new_state': 'SUBOPTIMAL'}

        # Action
        added_templates = \
            self.apis.add_template(ctx=None, templates=files_content,
                                   template_type=None, params=params)
        self.added_template = added_templates[0]['uuid']

        # Test assertions
        self.assertEqual('ERROR', added_templates[0]['status'])
        self.assertEqual('get_param called for a parameter that is not '
                         'defined in the \'parameters\' block',
                         added_templates[0]['status details'])

    def test_add_template_without_params(self):
        # Setup
        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITHOUT_PARAMS)
        files_content = [(template_path, self._load_yaml_file(template_path))]

        # Action
        added_templates = \
            self.apis.add_template(ctx=None, templates=files_content,
                                   template_type=None, params=None)
        self.added_template = added_templates[0]['uuid']

        # Test assertions
        self.assertThat(added_templates, matchers.HasLength(1))
        self.assertEqual('LOADING', added_templates[0]['status'])

    def test_add_template_with_extra_actual_param(self):
        # Setup
        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_PARAMS)
        files_content = [(template_path, self._load_yaml_file(template_path))]
        params = {'template_name': 'template_with_extra_actual_param',
                  'alarm_type': 'zabbix', 'alarm_name': 'My alarm',
                  'new_state': 'SUBOPTIMAL',
                  'non_existing_param': 'some value'}

        # Action
        added_templates = \
            self.apis.add_template(ctx=None, templates=files_content,
                                   template_type=None, params=params)
        self.added_template = added_templates[0]['uuid']

        # Test assertions
        self.assertThat(added_templates, matchers.HasLength(1))
        self.assertEqual('LOADING', added_templates[0]['status'])

    def test_add_template_with_extra_param_def(self):
        # Setup
        template_path = '%s/templates/parameters/%s' % (
            utils.get_resources_dir(),
            self.TEMPLATE_WITH_EXTRA_PARAM_DEF)
        files_content = [(template_path, self._load_yaml_file(template_path))]
        params = {'template_name': 'template_with_extra_param_def',
                  'alarm_type': 'zabbix', 'alarm_name': 'My alarm',
                  'new_state': 'SUBOPTIMAL'}

        # Action
        added_templates = \
            self.apis.add_template(ctx=None, templates=files_content,
                                   template_type=None, params=params)
        self.added_template = added_templates[0]['uuid']

        # Test assertions
        self.assertThat(added_templates, matchers.HasLength(1))
        self.assertEqual('LOADING', added_templates[0]['status'])

    def _assert_validate_template_result(self, expected_status,
                                         expected_status_code,
                                         expected_message, results):
        self.assertIsNotNone(results)
        results = json.loads(results)
        results = results['results']
        self.assertIsNotNone(results)
        self.assertThat(results, matchers.HasLength(1))
        self.assertEqual(expected_status, results[0]['status'])
        self.assertEqual(expected_status_code, results[0]['status code'])
        self.assertEqual(expected_message, results[0]['message'])

    def _delete_templates(self):
        if self.added_template:
            self.apis.delete_template(ctx=None, uuids=[self.added_template])
