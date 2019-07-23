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

from vitrage.datasources.zabbix.driver import ZabbixDriver
from vitrage.tests.mocks import mock_driver


class MockZabbixDriver(ZabbixDriver):
    """A zabbix driver for tests.

    Instead of calling Zabbix URL to get the data, it returns the data it
    is asked to
    """

    @staticmethod
    def get_event_types():
        return []

    def enrich_event(self, event, event_type):
        pass

    def __init__(self):
        super(MockZabbixDriver, self).__init__()
        self.alarm_datas = None

    def set_alarm_datas(self, alarm_datas):
        self.alarm_datas = alarm_datas

    def _get_alarms(self):
        alarms = []
        for alarm_data in self.alarm_datas:
            generators = mock_driver.simple_zabbix_alarm_generators(
                host_num=1,
                events_num=1,
                snap_vals=alarm_data)
            alarms.append(
                mock_driver.generate_sequential_events_list(generators)[0])

        return alarms
