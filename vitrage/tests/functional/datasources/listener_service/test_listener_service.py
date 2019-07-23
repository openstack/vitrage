# Copyright 2017 - Nokia
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
from vitrage.entity_graph.driver_exec import DriversNotificationEndpoint

from vitrage.datasources.driver_base import DriverBase
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver


class MyTestDriver(DriverBase):
    def __init__(self):
        super(MyTestDriver, self).__init__()

    def enrich_event(self, event, event_type):
        return event

    def get_all(self, datasource_action):
        pass

    @staticmethod
    def get_event_types():
        pass


class TestListenerService(base.BaseTest):

    def _add_event_to_actual_events(self, events):
        self.actual_events.extend(events)

    def _set_excepted_events(self, events):
        self.excepted_events = events
        self.actual_events = []

    def _assert_events(self):
        self.assert_list_equal(self.excepted_events, self.actual_events)

    def _generate_events(self, update_events):
        gen_list = mock_driver.simple_aodh_alarm_notification_generators(
            1, update_events=update_events)
        events = mock_driver.generate_sequential_events_list(gen_list)
        self.excepted_events = events
        self.actual_events = []
        return events

    def test_notification_listener_endpoints(self):

        my_test_driver = MyTestDriver()
        enrich_callbacks_by_events = {"mock": [my_test_driver.enrich_event]}
        endpoint = DriversNotificationEndpoint(
            self._add_event_to_actual_events)
        endpoint._enrich_event_methods = enrich_callbacks_by_events

        # test handling one event
        events = self._generate_events(1)
        endpoint.info(None, None, "mock", events[0], None)
        self._assert_events()

        # test handling list of events
        events = self._generate_events(2)
        endpoint.info(None, None, "mock", events, None)
        self._assert_events()
