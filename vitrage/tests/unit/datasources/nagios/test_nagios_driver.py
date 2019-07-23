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
from testtools import matchers

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import GraphAction
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources.nagios.properties import NagiosProperties as \
    NagiosProps
from vitrage.datasources.nagios.properties import NagiosTestStatus
from vitrage.tests.base import IsEmpty
from vitrage.tests.mocks import utils
from vitrage.tests.unit.datasources.nagios.mock_driver import MockNagiosDriver
from vitrage.tests.unit.datasources.nagios.nagios_base_test import \
    NagiosBaseTest


# noinspection PyProtectedMember
class NagiosDriverTest(NagiosBaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.CONFIG_FILE,
                   default=utils.get_resources_dir() +
                   '/nagios/nagios_conf.yaml',
                   help='Nagios configuration file'
                   ),
    ]

    def setUp(self):
        super(NagiosDriverTest, self).setUp()
        self.conf_reregister_opts(self.OPTS, NAGIOS_DATASOURCE)

    def test_get_all(self):
        """Check get_all functionality.

        Check the logic of which tests are returned: tests that are not OK,
        or tests that were changed from not-OK to OK
        """

        # Setup
        nagios_driver = MockNagiosDriver()

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_all_alarms()

        # Test assertions
        # Services with status OK should not be returned
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, IsEmpty())

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.WARNING}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.CRITICAL}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.WARNING}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(2))
        self._assert_contains(service_data1, services)
        self._assert_contains(service_data2, services)

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_all_alarms()

        # Test assertions
        # The services of service_data1/2 should be returned although their
        # status is OK, because they were not OK earlier
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(2))
        self._assert_contains(service_data1, services)
        self._assert_contains(service_data2, services)

        # Action
        services = nagios_driver._get_all_alarms()

        # Test assertions
        # Calling get_services again should not return anything, since all
        # services are still OK
        self.assertIsNotNone(services, 'services is None')
        self.assertThat(services, IsEmpty())

    def test_get_changes(self):
        """Check get_changes functionality.

        Check the logic of which tests are returned: tests that their status
        was changed since the last call
        """

        # Setup
        nagios_driver = MockNagiosDriver()

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_changed_alarms()

        # Test assertions
        # Services with status OK should not be returned
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, IsEmpty())

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.WARNING}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.CRITICAL}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.WARNING}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(2))
        self._assert_contains(service_data1, services)
        self._assert_contains(service_data2, services)

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.CRITICAL}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.CRITICAL}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data2, services)

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(2))
        self._assert_contains(service_data1, services)
        self._assert_contains(service_data2, services)

        # Action
        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'services is None')
        self.assertThat(services, IsEmpty())

    def test_get_changes_and_get_all(self):
        """Check get_changes and get_all functionalities """

        # Setup
        nagios_driver = MockNagiosDriver()

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.WARNING}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)

        # Action
        services = nagios_driver._get_changed_alarms()

        # Test assertions
        # Calling get_changes for the second time should return nothing
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, IsEmpty())

        # Action
        services = nagios_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)

        # Action
        services = nagios_driver._get_all_alarms()

        # Test assertions
        # Calling get_all for the second time should return the same results
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.CRITICAL}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.WARNING}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(2))
        self._assert_contains(service_data1, services)
        self._assert_contains(service_data2, services)

        # Action
        services = nagios_driver._get_changed_alarms()

        # Test assertions
        # Calling get_changes after get_all should return nothing
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, IsEmpty())

        # Action
        services = nagios_driver._get_all_alarms()

        # Test assertions
        # Calling get_all for the second time should return the same results
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(2))
        self._assert_contains(service_data1, services)
        self._assert_contains(service_data2, services)

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.CRITICAL}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.CRITICAL}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.CRITICAL}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(2))
        self._assert_contains(service_data2, services)
        self._assert_contains(service_data3, services)

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.WARNING}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.CRITICAL}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.CRITICAL}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)

        # Action
        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'services is None')
        self.assertThat(services, IsEmpty())

        # Action
        services = nagios_driver._get_all_alarms()

        # Test assertions
        # Calling get_all for the second time should return the same results
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(3))
        self._assert_contains(service_data1, services)
        self._assert_contains(service_data2, services)
        self._assert_contains(service_data3, services)

    def test_delete_service(self):
        """Check get_all and get_changes with a deleted service"""

        # Setup
        nagios_driver = MockNagiosDriver()

        # Action
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.WARNING}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}
        service_data3 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'Uptime',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1,
                                         service_data2,
                                         service_data3])

        services = nagios_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)

        # Action - delete a service that was OK
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.WARNING}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1, service_data2])

        services = nagios_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)

        # Action - delete a service that was not OK
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data2])

        services = nagios_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)
        self.assertEqual(GraphAction.DELETE_ENTITY,
                         services[0][DSProps.EVENT_TYPE])

        # Action - get changes, should not return the deleted alarm again
        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'services is None')
        self.assertThat(services, IsEmpty())

        # Action - "undelete" the service that was OK
        service_data1 = {NagiosProps.RESOURCE_NAME: 'compute-0',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.WARNING}
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data1, service_data2])

        services = nagios_driver._get_all_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)
        self.assertNotIn(DSProps.EVENT_TYPE, services[0])

        # Action - delete a service that was not OK and call get_changes
        service_data2 = {NagiosProps.RESOURCE_NAME: 'compute-1',
                         NagiosProps.SERVICE: 'CPU utilization',
                         NagiosProps.STATUS: NagiosTestStatus.OK}

        nagios_driver.set_service_datas([service_data2])

        services = nagios_driver._get_changed_alarms()

        # Test assertions
        self.assertIsNotNone(services, 'No services returned')
        self.assertThat(services, matchers.HasLength(1))
        self._assert_contains(service_data1, services)
        self.assertEqual(GraphAction.DELETE_ENTITY,
                         services[0][DSProps.EVENT_TYPE])
