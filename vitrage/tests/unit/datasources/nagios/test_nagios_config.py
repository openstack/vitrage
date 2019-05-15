# Copyright 2016 - Nokia
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

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.datasources.nagios.config import NagiosConfig
from vitrage.datasources.nagios.config import NagiosHostMapping
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.tests import base
from vitrage.tests.mocks import utils


class TestNagiosConfig(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.TRANSFORMER,
                   default='vitrage.datasources.nagios.transformer.'
                           'NagiosTransformer',
                   help='Nagios data source transformer class path',
                   required=True),
        cfg.StrOpt(DSOpts.DRIVER,
                   default='vitrage.datasources.nagios.driver.NagiosDriver',
                   help='Nagios driver class path',
                   required=True),
        cfg.IntOpt(DSOpts.CHANGES_INTERVAL,
                   default=30,
                   min=30,
                   help='interval between checking changes in nagios plugin',
                   required=True),
        cfg.StrOpt('user', default='nagiosadmin',
                   help='Nagios user name'),
        cfg.StrOpt('password', default='nagiosadmin',
                   help='Nagios user password'),
        cfg.StrOpt('url', default='', help='Nagios url'),
        cfg.StrOpt(DSOpts.CONFIG_FILE,
                   default=utils.get_resources_dir() +
                   '/nagios/nagios_conf.yaml',
                   help='Nagios configuration file'),
    ]

    # the mappings match the ones in nagios_conf.yaml
    MAPPING_1 = NagiosHostMapping('compute-1',
                                  NOVA_HOST_DATASOURCE,
                                  'compute-1')
    MAPPING_2 = NagiosHostMapping('compute-2', NOVA_HOST_DATASOURCE, 'host2')
    MAPPING_3 = NagiosHostMapping('compute-(.*)',
                                  NOVA_HOST_DATASOURCE,
                                  '${nagios_host}')
    MAPPING_4 = NagiosHostMapping('instance-(.*)',
                                  NOVA_INSTANCE_DATASOURCE,
                                  '${nagios_host}')
    MAPPINGS = [MAPPING_1, MAPPING_2, MAPPING_3, MAPPING_4]

    NON_EXISTING_MAPPING_1 = NagiosHostMapping('X',
                                               NOVA_HOST_DATASOURCE,
                                               'compute-1')
    NON_EXISTING_MAPPING_2 = NagiosHostMapping('compute-1',
                                               'X',
                                               'compute-1')
    NON_EXISTING_MAPPING_3 = NagiosHostMapping('compute-1',
                                               NOVA_HOST_DATASOURCE,
                                               'X')
    NON_EXISTING_MAPPINGS = [NON_EXISTING_MAPPING_1,
                             NON_EXISTING_MAPPING_2,
                             NON_EXISTING_MAPPING_3]

    def setUp(self):
        super(TestNagiosConfig, self).setUp()
        self.conf_reregister_opts(self.OPTS, NAGIOS_DATASOURCE)

    def test_nagios_configuration_loading(self):
        # Action
        nagios_conf = NagiosConfig()

        # Test assertions
        mappings = nagios_conf.mappings
        self.assertIsNotNone(nagios_conf, "no nagios configuration loaded")
        self.assertEqual(len(self.MAPPINGS), len(mappings))

        for expected_mapping in self.MAPPINGS:
            self.assertTrue(TestNagiosConfig._check_contains(expected_mapping,
                                                             mappings))
        for expected_mapping in self.NON_EXISTING_MAPPINGS:
            self.assertFalse(TestNagiosConfig._check_contains(expected_mapping,
                                                              mappings))

    def test_nagios_mapping(self):
        # check non-regexp mapping
        mapped_resource = self.MAPPING_1.map(None)
        self.assertIsNone(mapped_resource, 'expected None')

        mapped_resource = self.MAPPING_1.map('')
        self.assertIsNone(mapped_resource, 'expected None')

        mapped_resource = self.MAPPING_1.map('compute-1')
        self.assertIsNotNone(mapped_resource, 'expected Not None')
        self.assertEqual(self.MAPPING_1.resource_type, mapped_resource[0])
        self.assertEqual(self.MAPPING_1.resource_name, mapped_resource[1])

        mapped_resource = self.MAPPING_1.map('compute-2')
        self.assertIsNone(mapped_resource, 'expected None')

        # check mapping to a different resource name
        mapped_resource = self.MAPPING_2.map('compute-2')
        self.assertIsNotNone(mapped_resource, 'expected Not None')
        self.assertEqual(self.MAPPING_2.resource_type, mapped_resource[0])
        self.assertEqual(self.MAPPING_2.resource_name, mapped_resource[1])

        # check regexp mapping
        mapped_resource = self.MAPPING_3.map(None)
        self.assertIsNone(mapped_resource, 'expected None')

        mapped_resource = self.MAPPING_3.map('')
        self.assertIsNone(mapped_resource, 'expected None')

        mapped_resource = self.MAPPING_3.map('compute8')
        self.assertIsNone(mapped_resource, 'expected None')

        mapped_resource = self.MAPPING_3.map('compute-8')
        self.assertIsNotNone(mapped_resource, 'expected Not None')
        self.assertEqual(self.MAPPING_3.resource_type, mapped_resource[0])
        self.assertEqual('compute-8', mapped_resource[1])

        mapped_resource = self.MAPPING_3.map('instance-8')
        self.assertIsNone(mapped_resource, 'expected None')

    def test_get_vitrage_resource(self):
        """Test the resource returned after processing a list of mappings

        :return:
        """
        # Action
        nagios_conf = NagiosConfig()

        # Test assertions
        mapped_resource = nagios_conf.get_vitrage_resource(None)
        self.assertIsNone(mapped_resource, 'expected None')

        mapped_resource = nagios_conf.get_vitrage_resource('')
        self.assertIsNone(mapped_resource, 'expected None')

        mapped_resource = nagios_conf.get_vitrage_resource('compute-1')
        self.assertIsNotNone(mapped_resource, 'expected Not None')
        self.assertEqual(NOVA_HOST_DATASOURCE, mapped_resource[0])
        self.assertEqual('compute-1', mapped_resource[1])

        mapped_resource = nagios_conf.get_vitrage_resource('compute-2')
        self.assertIsNotNone(mapped_resource, 'expected Not None')
        self.assertEqual(NOVA_HOST_DATASOURCE, mapped_resource[0])
        self.assertEqual('host2', mapped_resource[1])

        mapped_resource = nagios_conf.get_vitrage_resource('compute-88')
        self.assertIsNotNone(mapped_resource, 'expected Not None')
        self.assertEqual(NOVA_HOST_DATASOURCE, mapped_resource[0])
        self.assertEqual('compute-88', mapped_resource[1])

        mapped_resource = nagios_conf.get_vitrage_resource('instance-7')
        self.assertIsNotNone(mapped_resource, 'expected Not None')
        self.assertEqual(NOVA_INSTANCE_DATASOURCE, mapped_resource[0])
        self.assertEqual('instance-7', mapped_resource[1])

    @staticmethod
    def _check_contains(expected_mapping, mappings):
        for mapping in mappings:
            if TestNagiosConfig._assert_equals(expected_mapping, mapping):
                return True
        return False

    @staticmethod
    def _assert_equals(mapping1, mapping2):
        return mapping1.nagios_host_regexp.pattern == \
            mapping2.nagios_host_regexp.pattern and \
            mapping1.resource_type == mapping2.resource_type and \
            mapping1.resource_name == mapping2.resource_name
