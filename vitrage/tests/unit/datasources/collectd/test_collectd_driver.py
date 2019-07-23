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

from datetime import datetime
from oslo_config import cfg

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.datasources.collectd import COLLECTD_DATASOURCE
from vitrage.datasources.collectd.driver import CollectdDriver
from vitrage.datasources.collectd.properties \
    import CollectdProperties as CProps
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver


# noinspection PyProtectedMember
WARN_SEVERITY = 'warning'
WARNING_EVENT_TYPE = 'collectd.alarm.warning'
HOST = 'compute-1'


class TestCollectdDriver(base.BaseTest):
    OPTS = []

    # noinspection PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(TestCollectdDriver, cls).setUpClass()
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=COLLECTD_DATASOURCE)

    # noinspection PyAttributeOutsideInit
    def setUp(self):
        super(TestCollectdDriver, self).setUp()
        self.driver = CollectdDriver()

    def test_enrich_event_with_alarm_up(self):
        now = datetime.now().isoformat()

        event = self._enrich_event(now, HOST,
                                   WARN_SEVERITY,
                                   WARNING_EVENT_TYPE)

        self._assert_event_equal(event, WARNING_EVENT_TYPE,
                                 HOST, WARN_SEVERITY, now)

    def _enrich_event(self, time_now, hostname, severity, event_type):
        event = self._generate_event(time_now, hostname, severity)
        event = self.driver.enrich_event(event, event_type)
        return event

    @staticmethod
    def _generate_event(time, hostname, severity):
        update_vals = {}
        if hostname:
            update_vals[CProps.HOST] = hostname
        if severity:
            update_vals[CProps.SEVERITY] = severity

        if time:
            update_vals[CProps.TIME] = time

        generators = mock_driver.simple_doctor_alarm_generators(
            update_vals=update_vals)

        return mock_driver.generate_sequential_events_list(generators)[0]

    def _assert_event_equal(self,
                            event,
                            expected_event_type,
                            expected_hostname,
                            expected_severity,
                            expected_sample_date):
        self.assertIsNotNone(event, 'No event returned')
        self.assertEqual(expected_hostname, event[CProps.HOST])
        self.assertEqual(expected_severity, event[CProps.SEVERITY])
        self.assertEqual(expected_sample_date, event[CProps.TIME])
        self.assertEqual(expected_event_type, event[DSProps.EVENT_TYPE])
