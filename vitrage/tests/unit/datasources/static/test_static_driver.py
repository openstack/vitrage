# Copyright 2016 - Nokia, ZTE
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

from oslo_config import cfg
from testtools import matchers

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import GraphAction
from vitrage.datasources.static import driver
from vitrage.datasources.static import STATIC_DATASOURCE
from vitrage.datasources.static import StaticFields
from vitrage.tests import base
from vitrage.tests.mocks import utils


class TestStaticDriver(base.BaseTest):

    CHANGES_DIR = '/changes_datasources'

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(TestStaticDriver, cls).setUpClass()
        cls.static_driver = driver.StaticDriver()

    def test_get_all(self):
        self._set_conf()

        # Action
        static_entities = self.static_driver.get_all(
            DatasourceAction.INIT_SNAPSHOT)

        # Test assertions
        self.assertThat(static_entities, matchers.HasLength(8))

        for entity in static_entities:
            self._validate_static_entity(entity)

    # noinspection PyAttributeOutsideInit
    def test_get_changes_with_added_resources(self):
        # Get initial resources
        self._set_conf(self.CHANGES_DIR + '/baseline')

        entities = self.static_driver.get_all(DatasourceAction.UPDATE)
        self.assertThat(entities, matchers.HasLength(4))

        # Add resources
        self._set_conf(self.CHANGES_DIR + '/added_resources')

        # Action
        changes = self.static_driver.get_changes(
            GraphAction.UPDATE_ENTITY)

        # Test Assertions
        expected_changes = [
            {'static_id': 's3', 'type': 'switch', 'name': 'switch-3 is new!',
             'id': '3333', 'state': 'available'},
            {'static_id': 'r2', 'type': 'router', 'name': 'router-2 is new!',
             'id': '2222', 'state': 'available'},
        ]

        self._validate_static_changes(expected_changes, changes)

    # noinspection PyAttributeOutsideInit
    def test_get_changes_with_deleted_resources(self):
        # Get initial resources
        self._set_conf(self.CHANGES_DIR + '/baseline')

        entities = self.static_driver.get_all(DatasourceAction.UPDATE)
        self.assertThat(entities, matchers.HasLength(4))

        # Delete resources
        self._set_conf(self.CHANGES_DIR + '/deleted_resources')

        # Action
        changes = self.static_driver.get_changes(
            GraphAction.UPDATE_ENTITY)

        # Test Assertions
        expected_changes = [
            {'static_id': 's2', 'type': 'switch', 'name': 'switch-2',
             'id': '23456', 'state': 'available',
             'vitrage_event_type': 'delete_entity'},
            {'static_id': 'h1', 'type': 'nova.host', 'id': '1',
             'vitrage_event_type': 'delete_entity'},
        ]

        self._validate_static_changes(expected_changes, changes)

    # noinspection PyAttributeOutsideInit
    def test_get_changes_with_changed_resources(self):
        # Get initial resources
        self._set_conf(self.CHANGES_DIR + '/baseline')

        entities = self.static_driver.get_all(DatasourceAction.UPDATE)
        self.assertThat(entities, matchers.HasLength(4))

        # Delete resources
        self._set_conf(self.CHANGES_DIR + '/changed_resources')

        # Action
        changes = self.static_driver.get_changes(
            GraphAction.UPDATE_ENTITY)

        # Test Assertions
        expected_changes = [
            {'static_id': 's1', 'type': 'switch', 'name': 'switch-1',
             'id': '12345', 'state': 'error'},
            {'static_id': 'r1', 'type': 'router',
             'name': 'router-1 is the best!', 'id': '45678'},
        ]

        self._validate_static_changes(expected_changes, changes)

    # noinspection PyAttributeOutsideInit
    def test_get_changes_with_mixed_changes(self):
        # Get initial resources
        self._set_conf(self.CHANGES_DIR + '/baseline')

        entities = self.static_driver.get_all(DatasourceAction.UPDATE)
        self.assertThat(entities, matchers.HasLength(4))

        # Delete resources
        self._set_conf(self.CHANGES_DIR + '/mixed_changes')

        # Action
        changes = self.static_driver.get_changes(
            GraphAction.UPDATE_ENTITY)

        # Test Assertions
        expected_changes = [
            {'static_id': 's1', 'type': 'switch', 'name': 'switch-1',
             'id': '12345', 'state': 'available',
             'vitrage_event_type': 'delete_entity'},
            {'static_id': 's2', 'type': 'switch', 'name': 'switch-2',
             'id': '23456', 'state': 'error'},
            {'static_id': 'r2', 'type': 'router', 'name': 'router-2 is new!',
             'id': '222'},
        ]

        self._validate_static_changes(expected_changes, changes)

    def _validate_static_entity(self, entity):
        self.assertIsInstance(entity[StaticFields.METADATA], dict)
        for rel in entity[StaticFields.RELATIONSHIPS]:
            self._validate_static_rel(entity, rel)

    def _validate_static_rel(self, entity, rel):
        self.assertTrue(entity[StaticFields.STATIC_ID] in
                        (rel[StaticFields.SOURCE], rel[StaticFields.TARGET]))
        self.assertTrue(
            isinstance(rel[StaticFields.SOURCE], dict)
            and entity[StaticFields.STATIC_ID] == rel[StaticFields.TARGET]
            or isinstance(rel[StaticFields.TARGET], dict)
            and entity[StaticFields.STATIC_ID] == rel[StaticFields.SOURCE]
            or entity[StaticFields.STATIC_ID] == rel[StaticFields.SOURCE]
            and entity[StaticFields.STATIC_ID] == rel[StaticFields.TARGET])

    def _validate_static_changes(self, expected_changes, changes):
        self.assertThat(changes, matchers.HasLength(len(expected_changes)))

        for entity in changes:
            self._validate_static_entity(entity)

        for expected_change in expected_changes:
            found = False
            for change in changes:
                if change[StaticFields.TYPE] == \
                        expected_change[StaticFields.TYPE] and \
                        change[StaticFields.ID] == \
                        expected_change[StaticFields.ID]:
                    found = True
                    self.assertEqual(expected_change.get('vitrage_event_type'),
                                     change.get('vitrage_event_type'))
                    self.assertEqual(expected_change.get(StaticFields.NAME),
                                     change.get(StaticFields.NAME))
                    self.assertEqual(expected_change.get(StaticFields.STATE),
                                     change.get(StaticFields.STATE))
            self.assertTrue(found)

    def _set_conf(self, sub_dir=None):
        default_dir = utils.get_resources_dir() + \
            '/static_datasources' + (sub_dir if sub_dir else '')

        opts = [
            cfg.StrOpt(DSOpts.TRANSFORMER,
                       default='vitrage.datasources.static.transformer.'
                               'StaticTransformer'),
            cfg.StrOpt(DSOpts.DRIVER,
                       default='vitrage.datasources.static.driver.'
                               'StaticDriver'),
            cfg.IntOpt(DSOpts.CHANGES_INTERVAL,
                       default=30,
                       min=30,
                       help='interval between checking changes in the static '
                            'datasources'),
            cfg.StrOpt('directory', default=default_dir),
        ]

        self.conf_reregister_opts(opts, group=STATIC_DATASOURCE)
