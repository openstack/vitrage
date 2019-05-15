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

import copy

from oslo_config import cfg
from testtools import matchers

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import GraphAction
from vitrage.datasources.zabbix.properties import ZabbixProperties as ZProps
from vitrage.datasources.zabbix import ZABBIX_DATASOURCE
from vitrage.tests.base import IsEmpty
from vitrage.tests.mocks import utils
from vitrage.tests.unit.datasources.zabbix.mock_driver import MockZabbixDriver
from vitrage.tests.unit.datasources.zabbix.zabbix_base_test import \
    ZabbixBaseTest


# noinspection PyProtectedMember
class ZabbixDriverTest(ZabbixBaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.CONFIG_FILE,
                   help='Zabbix configuration file',
                   default=utils.get_resources_dir()
                        + '/zabbix/zabbix_conf.yaml'),
    ]

    def setUp(self):
        super(ZabbixDriverTest, self).setUp()
        self.conf_reregister_opts(self.OPTS, group=ZABBIX_DATASOURCE)

    def test_get_all(self):
        # Test Setup
        zabbix_driver = MockZabbixDriver()

        alarm_data1 = self._extract_alarm_data(triggerid='1', status='1')
        alarm_data2 = self._extract_alarm_data(triggerid='2', status='1',
                                               value='1')
        alarm_data3 = self._extract_alarm_data(triggerid='3', value='1')
        alarm_data4 = self._extract_alarm_data(triggerid='4')

        zabbix_driver.set_alarm_datas([alarm_data1,
                                       alarm_data2,
                                       alarm_data3,
                                       alarm_data4])
        # Test Action
        alarms = zabbix_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(1))
        self._assert_contains(alarm_data3, alarms)

    def test_get_all_functionality(self):

        # Step 1 - Services with status OK should not be returned
        # Test setup scenario
        zabbix_driver = MockZabbixDriver()

        alarm_data1 = self._extract_alarm_data()
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2')
        alarm_data3 = self._extract_alarm_data(z_resource_name='compute-2',
                                               triggerid='2')

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        # Test action
        alarms = zabbix_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, IsEmpty())

        # Step 2 - one raised alarm
        # Test setup
        alarm_data1 = self._extract_alarm_data(value='1')

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        # Test action
        alarms = zabbix_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(1))
        self._assert_contains(alarm_data1, alarms)

        # Step 3 - two raised alarms
        # Test setup
        alarm_data1 = self._extract_alarm_data(value='1', priority='4')
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2',
                                               value='1')

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        expected_alarm1 = alarm_data1
        expected_alarm2 = copy.copy(alarm_data2)
        expected_alarm2[ZProps.RESOURCE_NAME] = 'host2'

        # Test action
        alarms = zabbix_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(2))
        self._assert_contains(expected_alarm1, alarms)
        self._assert_contains(expected_alarm2, alarms)

        # Step 4 - Check inactive alarms. Get all function should return
        # inactive alarm (alarm that its status has changed to OK)
        # Test setup
        alarm_data1 = self._extract_alarm_data()
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2')

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        expected_alarm1 = alarm_data1
        expected_alarm2 = copy.copy(alarm_data2)
        expected_alarm2[ZProps.RESOURCE_NAME] = 'host2'

        # Test action
        alarms = zabbix_driver._get_all_alarms()

        # Test assertions
        # The alarms of alarm_data1/2 should be returned although their
        # status is OK, because they were not OK earlier
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(2))
        self._assert_contains(expected_alarm1, alarms)
        self._assert_contains(expected_alarm2, alarms)

        # Step 4 - get all when all alarms are inactivated and their status
        # was not changed

        # Test action
        alarms = zabbix_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'alarms is None')
        self.assertThat(alarms, IsEmpty())

    def test_get_changes_functionality(self):

        # Step 1 - get changes when all alarms are OK
        # Test setup
        zabbix_driver = MockZabbixDriver()

        alarm_data1 = self._extract_alarm_data(priority='2')
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2',
                                               priority='2')
        alarm_data3 = self._extract_alarm_data(z_resource_name='compute-2',
                                               description='Uptime',
                                               priority='3')

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        # Test action
        alarms = zabbix_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, IsEmpty())

        # Step 2 - get changes when alarm is raised
        # Test setup
        alarm_data1 = self._extract_alarm_data(priority='2', value='1')

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        # Test action
        alarms = zabbix_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(1))
        self._assert_contains(alarm_data1, alarms)

        # Step 3 - get changes when the priority of inactive alarm is changed
        # Test setup
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2',
                                               priority='3')
        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        # Test action
        alarms = zabbix_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, IsEmpty())

        # Step 4 - get changes when:
        # 1. alarm1 - priority of active alarm is changed (should be returned)
        # 2. alarm2 - raised alarm (should be returned)
        # 3. alarm3 - priority of inactive alarm is changed (should not
        #             be returned)
        # Test setup
        alarm_data1 = self._extract_alarm_data(priority='4', value='1')
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2',
                                               priority='1', value='1')
        alarm_data3 = self._extract_alarm_data(z_resource_name='compute-2',
                                               triggerid='22222',
                                               priority='1')

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        expected_alarm1 = alarm_data1
        expected_alarm2 = copy.copy(alarm_data2)
        expected_alarm2[ZProps.RESOURCE_NAME] = 'host2'

        # Test action
        alarms = zabbix_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(2))
        self._assert_contains(expected_alarm1, alarms)
        self._assert_contains(expected_alarm2, alarms)

        # Step 5 - get changes when all active alarms are changed to inactive
        # Test setup
        alarm_data1 = self._extract_alarm_data(priority='4')
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2',
                                               priority='1')

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        expected_alarm1 = alarm_data1
        expected_alarm2 = copy.copy(alarm_data2)
        expected_alarm2[ZProps.RESOURCE_NAME] = 'host2'

        # Test action
        alarms = zabbix_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(2))
        self._assert_contains(expected_alarm1, alarms)
        self._assert_contains(expected_alarm2, alarms)

        # Step 6 - get changes when no change occurred
        # Action
        alarms = zabbix_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(alarms, 'alarms is None')
        self.assertThat(alarms, IsEmpty())

    def test_get_changes_and_get_all(self):

        # Step 1 - get changes
        # Step setup
        zabbix_driver = MockZabbixDriver()

        alarm_data1 = self._extract_alarm_data(priority='2', value='1')
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2',
                                               priority='2')
        alarm_data3 = self._extract_alarm_data(z_resource_name='compute-2',
                                               triggerid='2')
        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        # Step action
        alarms = zabbix_driver._get_changed_alarms()

        # Step assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(1))
        self._assert_contains(alarm_data1, alarms)

        # Step 2 - get changes when no change occurred (returns nothing)
        # Step action
        alarms = zabbix_driver._get_changed_alarms()

        # Step assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, IsEmpty())

        # Step 3 - get all
        # Step action
        alarms = zabbix_driver._get_all_alarms()

        # Step assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(1))
        self._assert_contains(alarm_data1, alarms)

        # Step 4 - get all for second time
        # (when no change has occurred it returns the same)
        # Step action
        alarms = zabbix_driver._get_all_alarms()

        # Step assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(1))
        self._assert_contains(alarm_data1, alarms)

        # Step 5 - calling get changes right after get all (returns nothing)
        # Step setup
        alarm_data1 = self._extract_alarm_data(priority='4', value='1')
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2',
                                               priority='1',
                                               value='1')

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        expected_alarm1 = alarm_data1
        expected_alarm2 = copy.copy(alarm_data2)
        expected_alarm2[ZProps.RESOURCE_NAME] = 'host2'

        # Step action
        get_all_alarms = zabbix_driver._get_all_alarms()
        changed_alarms = zabbix_driver._get_changed_alarms()

        # Step assertions
        self.assertIsNotNone(get_all_alarms, 'No alarms returned')
        self.assertThat(get_all_alarms, matchers.HasLength(2))
        self._assert_contains(expected_alarm1, get_all_alarms)
        self._assert_contains(expected_alarm2, get_all_alarms)

        self.assertIsNotNone(changed_alarms, 'No alarms returned')
        self.assertThat(changed_alarms, IsEmpty())

        # Step 6 - get changes
        # Step setup
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2',
                                               priority='4',
                                               value='1')
        alarm_data3 = self._extract_alarm_data(z_resource_name='compute-2',
                                               triggerid='2',
                                               priority='4',
                                               value='1')

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])

        expected_alarm1 = copy.copy(alarm_data2)
        expected_alarm1[ZProps.RESOURCE_NAME] = 'host2'
        expected_alarm2 = copy.copy(expected_alarm1)
        expected_alarm2[ZProps.TRIGGER_ID] = '2'

        # Step action
        alarms = zabbix_driver._get_changed_alarms()

        # Step assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(2))
        self._assert_contains(expected_alarm1, alarms)
        self._assert_contains(expected_alarm2, alarms)

    def test_delete_alarm(self):

        # Test setup
        alarm_data1 = self._extract_alarm_data(value='1')
        alarm_data2 = self._extract_alarm_data(z_resource_name='compute-2')
        alarm_data3 = self._extract_alarm_data(z_resource_name='compute-2',
                                               triggerid='2')

        # Step 1 - delete inactive alarm
        # Step setup
        zabbix_driver = MockZabbixDriver()

        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2, alarm_data3])
        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2])

        # Step action
        alarms = zabbix_driver._get_all_alarms()

        # Step assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(1))
        self._assert_contains(alarm_data1, alarms)

        # Step 2 - delete active alarm
        # Step setup
        zabbix_driver.set_alarm_datas([alarm_data2])

        # Step action
        alarms = zabbix_driver._get_all_alarms()

        # Step assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(1))
        self._assert_contains(alarm_data1, alarms)
        self.assertEqual(GraphAction.DELETE_ENTITY,
                         alarms[0][DSProps.EVENT_TYPE])

        # Step 3 - get changes after get all should not return deleted alarm
        # Step action
        alarms = zabbix_driver._get_changed_alarms()

        # Step assertions
        self.assertIsNotNone(alarms, 'alarms is None')
        self.assertThat(alarms, IsEmpty())

        # Step 4 -
        # Step setup
        zabbix_driver.set_alarm_datas([alarm_data1, alarm_data2])
        zabbix_driver._get_all_alarms()
        zabbix_driver.set_alarm_datas([alarm_data2])

        # Step action
        alarms = zabbix_driver._get_changed_alarms()

        # Step assertions
        self.assertIsNotNone(alarms, 'No alarms returned')
        self.assertThat(alarms, matchers.HasLength(1))
        self._assert_contains(alarm_data1, alarms)
        self.assertEqual(GraphAction.DELETE_ENTITY,
                         alarms[0][DSProps.EVENT_TYPE])

    def _extract_alarm_data(self,
                            z_resource_name='compute-1',
                            description='cpu',
                            status='0',
                            value='0',
                            priority='1',
                            triggerid='0'):

        return {ZProps.ZABBIX_RESOURCE_NAME: z_resource_name,
                ZProps.DESCRIPTION: description,
                ZProps.STATUS: status,
                ZProps.VALUE: value,
                ZProps.PRIORITY: priority,
                ZProps.RESOURCE_NAME: z_resource_name,
                ZProps.TRIGGER_ID: triggerid}
