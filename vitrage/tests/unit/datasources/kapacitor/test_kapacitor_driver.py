# Copyright 2019 - Viettel
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
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.datasources.kapacitor.driver import KapacitorDriver
from vitrage.datasources.kapacitor import KAPACITOR_DATASOURCE
from vitrage.datasources.kapacitor.properties \
    import KapacitorProperties as KProps
from vitrage.datasources.kapacitor.properties \
    import KapacitorState as KState
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver
from vitrage.tests.mocks import utils

# notification alarm input
HOST = 'compute-1'
ALARM_PRIntORIY = 'critical'
ALARM_EVENT_TYPE = 'kapacitor.alarm.critical'

# match result
EXPECTED_RESOURCE_TYPE = 'nova.host'
EXPECTED_RESOURCE_NAME = 'compute1'
EXPECTED_EVENT_PRIORIY = 'critical'
EXPECTED_EVENT_TYPE = 'kapacitor.alarm.critical'


class TestKapacitorDriver(base.BaseTest):
    OPTS = [
        cfg.StrOpt(DSOpts.CONFIG_FILE,
                   help='Kapacitor configuration file',
                   default=utils.get_resources_dir()
                   + '/kapacitor/kapacitor_conf.yaml'),
    ]

    def setUp(self):
        super(TestKapacitorDriver, self).setUp()
        self.conf_reregister_opts(self.OPTS, group=KAPACITOR_DATASOURCE)
        self.driver = KapacitorDriver()

    def test_enrich_event(self):
        # Test event on host
        # Setup
        input_data = {KProps.HOST: 'compute-1',
                      KProps.PRIORITY: 'CPU utilization',
                      ALARM_EVENT_TYPE: KState.CRITICAL}
        expected_data = {DSProps.EVENT_TYPE: KState.CRITICAL,
                         KProps.RESOURCE_NAME: 'compute-1',
                         KProps.RESOURCE_TYPE: 'nova.host',
                         KProps.PRIORITY: 'CPU utilization'}
        event = self._generate_event(input_data[KProps.HOST],
                                     input_data[KProps.PRIORITY])
        # Action
        event = self.driver.enrich_event(event,
                                         input_data[ALARM_EVENT_TYPE])
        # Test assertions
        self._assert_event_equal(event, expected_data)

        # Test event on instance
        # Setup
        input_data = {KProps.HOST: 'node1-vm',
                      KProps.PRIORITY: 'CPU utilization',
                      ALARM_EVENT_TYPE: KState.CRITICAL}
        expected_data = {DSProps.EVENT_TYPE: KState.CRITICAL,
                         KProps.RESOURCE_NAME: 'node1-vm',
                         KProps.RESOURCE_TYPE: 'nova.instance',
                         KProps.PRIORITY: 'CPU utilization'}
        event = self._generate_event(input_data[KProps.HOST],
                                     input_data[KProps.PRIORITY])
        # Action
        event = self.driver.enrich_event(event,
                                         input_data[ALARM_EVENT_TYPE])
        # Test assertions
        self._assert_event_equal(event, expected_data)

    @staticmethod
    def _generate_event(hostname, priority):
        update_vals = {}
        if hostname:
            update_vals[KProps.HOST] = hostname
        if priority:
            update_vals[KProps.PRIORITY] = priority

        generators = mock_driver.simple_kapacitor_alarm_generators(
            update_vals=update_vals)

        return mock_driver.generate_sequential_events_list(generators)[0]

    def _assert_event_equal(self,
                            event1,
                            event2):
        self.assertIsNotNone(event1, 'No event returned')
        self.assertEqual(event1[DSProps.EVENT_TYPE],
                         event2[DSProps.EVENT_TYPE])
        self.assertEqual(event1[KProps.RESOURCE_NAME],
                         event2[KProps.RESOURCE_NAME])
        self.assertEqual(event1[KProps.RESOURCE_TYPE],
                         event2[KProps.RESOURCE_TYPE])
        self.assertEqual(event1[KProps.PRIORITY],
                         event2[KProps.PRIORITY])
