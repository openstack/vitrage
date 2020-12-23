# Copyright 2018 - Nokia
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

# noinspection PyPackageRequirements
from unittest import mock

from oslo_config import cfg
# noinspection PyPackageRequirements
from testtools import matchers

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EventProperties as EProps
from vitrage.datasources.prometheus.driver import PROMETHEUS_EVENT_TYPE
from vitrage.datasources.prometheus.driver import PrometheusDriver
from vitrage.datasources.prometheus import PROMETHEUS_DATASOURCE
from vitrage.datasources.prometheus.properties \
    import PrometheusDatasourceProperties as PDProps
from vitrage.datasources.prometheus.properties \
    import PrometheusProperties as PProps
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver
from vitrage.tests.mocks import utils


# noinspection PyProtectedMember
class PrometheusDriverTest(base.BaseTest):
    CONFIG_PATH = '/prometheus/prometheus_conf.yaml'
    OPTS = [
        cfg.StrOpt(
            DSOpts.CONFIG_FILE,
            help='Prometheus configuration file',
            default=utils.get_resources_dir() + CONFIG_PATH),
    ]

    def setUp(self):
        super(PrometheusDriverTest, self).setUp()
        self.conf_reregister_opts(self.OPTS, group=PROMETHEUS_DATASOURCE)

    @mock.patch('socket.gethostbyaddr')
    def test_adjust_label_value(self, mock_socket):

        # Test setup
        hostname = 'devstack-rocky-release-4'
        mock_socket.return_value = [hostname]
        driver = PrometheusDriver()
        valid_ip = '127.0.0.1'
        not_ip = 'localhost'
        invalid_ip = '127.1'

        # Test Action
        observed_valid_ip = driver._adjust_label_value(valid_ip)
        observed_not_ip = driver._adjust_label_value(not_ip)
        observed_invalid_ip = driver._adjust_label_value(invalid_ip)

        # Test assertions
        self.assertEqual(hostname, observed_valid_ip)
        self.assertEqual(not_ip, observed_not_ip)
        self.assertEqual(invalid_ip, observed_invalid_ip)

    @mock.patch('socket.gethostbyaddr')
    def test_calculate_host_vitrage_entity_unique_props(self, mock_socket):
        # First alert is 'AvgCPUTimeOnIdleMode' on host
        # Second alert is 'HighInodeUsage' on host

        # Test setup
        hostname = 'devstack-rocky-release-4'
        mock_socket.return_value = [hostname]
        driver = PrometheusDriver()
        alerts = self._generate_alerts()
        host_alert_1 = alerts[0]
        host_alert_2 = alerts[1]

        # Test Action
        observed_host_alert_1 = \
            driver._calculate_vitrage_entity_unique_props(host_alert_1)
        observed_host_alert_2 = \
            driver._calculate_vitrage_entity_unique_props(host_alert_2)

        # Test assertion
        expected = {'id': hostname}
        self.assertEqual(expected, observed_host_alert_1)
        self.assertEqual(expected, observed_host_alert_2)

    @mock.patch('socket.gethostbyaddr')
    def test_calculate_vm_vitrage_entity_unique_props(self, mock_socket):
        # First alert is 'HighTrafficOnBridge' on vm
        # Second alert is 'HighCpuOnVmAlert' on vm

        # Test setup
        hostname = 'devstack-rocky-release-4'
        mock_socket.return_value = [hostname]
        driver = PrometheusDriver()
        alerts = self._generate_alerts()
        vm_alert_1 = alerts[2]
        vm_alert_2 = alerts[3]

        # Test Action
        observed_vm_alert_1 = \
            driver._calculate_vitrage_entity_unique_props(vm_alert_1)
        observed_vm_alert_2 = \
            driver._calculate_vitrage_entity_unique_props(vm_alert_2)

        # Test assertion
        expected = {'instance_name': 'instance-00000005',
                    'host_id': hostname}
        self.assertEqual(expected, observed_vm_alert_1)
        self.assertEqual(expected, observed_vm_alert_2)

    def test_get_resource_alert_values(self):

        # Test setup
        driver = PrometheusDriver()
        alerts = self._generate_alerts()
        alert_1 = alerts[0]
        alert_2 = alerts[3]

        # Test Action
        observed_alert_1 = driver._get_resource_alert_values(alert_1)
        observed_alert_2 = driver._get_resource_alert_values(alert_2)

        # Test assertions
        expected_alert_1 = {'instance': '135.248.18.109:9100'}
        expected_alert_2 = {'instance': '135.248.18.109:9177',
                            'domain': 'instance-00000005'}
        self.assertEqual(expected_alert_1, observed_alert_1)
        self.assertEqual(expected_alert_2, observed_alert_2)

    def test_get_conf_resource(self):

        # Test setup
        driver = PrometheusDriver()
        alerts = self._generate_alerts()
        alert_1 = alerts[0]
        alert_2 = alerts[3]

        # Test Action
        observed_alert_1 = driver._get_conf_resource(alert_1)
        observed_alert_2 = driver._get_conf_resource(alert_2)

        # Test assertions
        expected_alert_1 = {'id': 'instance'}
        expected_alert_2 = {'instance_name': 'domain',
                            'host_id': 'instance'}
        self.assertEqual(expected_alert_1, observed_alert_1)
        self.assertEqual(expected_alert_2, observed_alert_2)

    def test_validate_ip(self):

        # Test setup
        driver = PrometheusDriver()
        ipv4_without_port = '1.1.1.1'
        ipv4_with_port = '1.1.1.1:1'
        invalid_ipv4 = '1.1'
        ipv6_without_port = '2001:db8::'
        ipv6_with_port = '[2001:db8::]:11'
        invalid_ipv6 = '2001:db8:'
        not_ip = 'not ip'

        # Test Action
        observed_ipv4_without_port = driver._validate_ip(ipv4_without_port)
        observed_ipv4_with_port = driver._validate_ip(ipv4_with_port)
        observed_ipv6_without_port = driver._validate_ip(ipv6_without_port)
        ipv6_with_port = driver._validate_ip(ipv6_with_port)

        # Test assertions
        self.assertIsNotNone(observed_ipv4_without_port)
        self.assertIsNotNone(observed_ipv4_with_port)
        self.assertIsNotNone(observed_ipv6_without_port)
        self.assertIsNotNone(ipv6_with_port)
        self.assertRaises(ValueError, driver._validate_ip, invalid_ipv4)
        self.assertRaises(ValueError, driver._validate_ip, invalid_ipv6)
        self.assertRaises(ValueError, driver._validate_ip, not_ip)

    @mock.patch('vitrage.datasources.prometheus.driver.'
                'PrometheusDriver.nova_client')
    @mock.patch('socket.gethostbyaddr')
    def test_enrich_event(self, mock_socket, mock_nova_client):

        # Test setup
        mock_nova_client.servers.list.return_value = None
        mock_socket.return_value = ['devstack-rocky-release-4']
        driver = PrometheusDriver()
        event = self._generate_event()

        # Test Action
        created_events = driver.enrich_event(event, PROMETHEUS_EVENT_TYPE)

        # Test assertions
        self._assert_event_equal(created_events, PROMETHEUS_EVENT_TYPE)

    def _assert_event_equal(self,
                            created_events,
                            expected_event_type):
        self.assertIsNotNone(created_events, 'No events returned')
        self.assertThat(created_events, matchers.HasLength(6),
                        'Expected 6 events')
        for event in created_events:
            self.assertEqual(expected_event_type,
                             event[DSProps.EVENT_TYPE])
            self.assertIsNotNone(event[PDProps.ENTITY_UNIQUE_PROPS])

    def _generate_alerts(self):
        event = self._generate_event()
        details = event[EProps.DETAILS]
        return details[PProps.ALERTS]

    @staticmethod
    def _generate_event(update_vals=None):
        generators = mock_driver.simple_prometheus_alarm_generators(
            update_vals=update_vals)

        return mock_driver.generate_sequential_events_list(generators)[0]
