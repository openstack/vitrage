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
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.zabbix.driver import ZabbixDriver
from vitrage.datasources.zabbix.properties import ZabbixProperties \
    as ZabbixProps
from vitrage.datasources.zabbix import ZABBIX_DATASOURCE
from vitrage.tests import base
from vitrage.tests.mocks import utils


class TestZabbixConfig(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.TRANSFORMER,
                   default='vitrage.datasources.zabbix.transformer.'
                           'ZabbixTransformer',
                   help='Zabbix data source transformer class path',
                   required=True),
        cfg.StrOpt(DSOpts.DRIVER,
                   default='vitrage.datasources.zabbix.driver.ZabbixDriver',
                   help='Zabbix driver class path',
                   required=True),
        cfg.IntOpt(DSOpts.CHANGES_INTERVAL,
                   default=30,
                   min=30,
                   help='interval between checking changes in zabbix plugin',
                   required=True),
        cfg.StrOpt('user', default='admin',
                   help='Zabbix user name'),
        cfg.StrOpt('password', default='zabbix',
                   help='Zabbix user password'),
        cfg.StrOpt('url', default='', help='Zabbix url'),
        cfg.StrOpt(DSOpts.CONFIG_FILE,
                   help='Zabbix configuration file',
                   default=utils.get_resources_dir()
                        + '/zabbix/zabbix_conf.yaml'),
    ]

    # the mappings match the ones in zabbix_conf.yaml
    MAPPINGS = {
        'compute-1': {ZabbixProps.RESOURCE_TYPE: NOVA_HOST_DATASOURCE,
                      ZabbixProps.RESOURCE_NAME: 'compute-1'},
        'compute-2': {ZabbixProps.RESOURCE_TYPE: NOVA_HOST_DATASOURCE,
                      ZabbixProps.RESOURCE_NAME: 'host2'},
    }

    NON_EXISTING_MAPPINGS = {
        'X': {ZabbixProps.RESOURCE_TYPE: NOVA_HOST_DATASOURCE,
              ZabbixProps.RESOURCE_NAME: 'compute-1'},
        'compute-1': {ZabbixProps.RESOURCE_TYPE: 'X',
                      ZabbixProps.RESOURCE_NAME: 'compute-1'},
    }

    def setUp(self):
        super(TestZabbixConfig, self).setUp()
        self.conf_reregister_opts(self.OPTS, group=ZABBIX_DATASOURCE)

    def test_zabbix_configuration_loading(self):
        # Action
        mappings = ZabbixDriver._configuration_mapping()

        # Test assertions
        self.assertEqual(len(self.MAPPINGS), len(mappings))

        for expected_mapping in self.MAPPINGS.items():
            self.assertTrue(self._check_contains(expected_mapping, mappings))
        for expected_mapping in self.NON_EXISTING_MAPPINGS.items():
            self.assertFalse(self._check_contains(expected_mapping, mappings))

    @staticmethod
    def _check_contains(expected_mapping, mappings):
        for mapping in mappings.items():
            if expected_mapping == mapping:
                return True
        return False
