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
from vitrage.common.constants import EventProperties as EventProps
from vitrage.datasources.doctor import DOCTOR_DATASOURCE
from vitrage.datasources.doctor.driver import DoctorDriver
from vitrage.datasources.doctor.properties import DoctorDetails
from vitrage.datasources.doctor.properties import DoctorProperties \
    as DoctorProps
from vitrage.datasources.doctor.properties import DoctorStatus
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver


# noinspection PyProtectedMember
class DoctorDriverTest(base.BaseTest):
    OPTS = []

    # noinspection PyPep8Naming
    @classmethod
    def setUpClass(cls):
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=DOCTOR_DATASOURCE)

    def test_enrich_event(self):
        # Test setup
        driver = DoctorDriver()
        event_type = DoctorProps.HOST_DOWN

        time1 = datetime.now().isoformat()
        host1 = 'host1'
        event = self._generate_event(time1, host1, DoctorStatus.DOWN)

        # Enrich event
        event = driver.enrich_event(event, event_type)

        # Test assertions
        self._assert_event_equal(event, event_type, host1,
                                 DoctorStatus.DOWN, time1, time1)

        # Add another event
        time2 = datetime.now().isoformat()
        host2 = 'host2'
        event = self._generate_event(time2, host2, DoctorStatus.DOWN)

        # Enrich event
        event = driver.enrich_event(event, event_type)

        # Test assertions
        self._assert_event_equal(event, event_type, host2,
                                 DoctorStatus.DOWN, time2, time2)

        # Change the first event to 'up' - should be marked as deleted
        time3 = datetime.now().isoformat()
        event = self._generate_event(time3, host1, DoctorStatus.UP)

        # Enrich event
        event = driver.enrich_event(event, event_type)

        # Test assertions
        self._assert_event_equal(event, event_type, host1,
                                 DoctorStatus.UP, time3, time3)

        # Send again the second event. The sample time should be new, but the
        # update time should remain with its old value (since the state has
        # not changed)
        time4 = datetime.now().isoformat()
        event = self._generate_event(time4, host2, DoctorStatus.DOWN)

        # Enrich event
        event = driver.enrich_event(event, event_type)

        # Test assertions
        self._assert_event_equal(event, event_type, host2,
                                 DoctorStatus.DOWN, time4, time2)

        # Send again the first event, after it was deleted. Make sure it is
        # raised again
        time5 = datetime.now().isoformat()
        event = self._generate_event(time5, host1, DoctorStatus.DOWN)

        # Enrich event
        event = driver.enrich_event(event, event_type)

        # Test assertions
        self._assert_event_equal(event, event_type, host1,
                                 DoctorStatus.DOWN, time5, time5)

    @staticmethod
    def _generate_event(time, hostname, status):
        details = {}
        if hostname:
            details[DoctorDetails.HOSTNAME] = hostname
        if status:
            details[DoctorDetails.STATUS] = status

        update_vals = {EventProps.DETAILS: details}
        if time:
            update_vals[EventProps.TIME] = time

        generators = mock_driver.simple_doctor_alarm_generators(
            update_vals=update_vals)

        return mock_driver.generate_sequential_events_list(generators)[0]

    def _assert_event_equal(self,
                            event,
                            expected_event_type,
                            expected_hostname,
                            expected_status,
                            expected_sample_date,
                            expected_update_date):
        self.assertIsNotNone(event, 'No event returned')
        self.assertEqual(expected_hostname,
                         event[EventProps.DETAILS][DoctorDetails.HOSTNAME])
        self.assertEqual(expected_status,
                         event[EventProps.DETAILS][DoctorDetails.STATUS])
        self.assertEqual(expected_sample_date, event[EventProps.TIME])
        self.assertEqual(expected_update_date, event[DoctorProps.UPDATE_TIME])
        self.assertEqual(expected_event_type, event[DSProps.EVENT_TYPE])
