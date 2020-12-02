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

from vitrage.datasources.nagios.parser import NagiosParser
from vitrage.datasources.nagios.properties import NagiosProperties
from vitrage.datasources.nagios.properties import NagiosTestStatus
from vitrage.tests.mocks import utils
from vitrage.tests.unit.datasources.nagios.nagios_base_test \
    import NagiosBaseTest


class NagiosParserTest(NagiosBaseTest):

    expected_service1 = {NagiosProperties.RESOURCE_NAME: 'compute-0-0.local',
                         NagiosProperties.SERVICE: 'CPU load',
                         NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                         NagiosProperties.LAST_CHECK: '2016-02-09 13:05:32',
                         NagiosProperties.DURATION: ' 8d  2h 16m 33s',
                         NagiosProperties.ATTEMPT: '1/1',
                         NagiosProperties.STATUS_INFO:
                             'high CPU load\xa0'}

    expected_service2 = {NagiosProperties.RESOURCE_NAME: 'compute-0-1.local',
                         NagiosProperties.SERVICE: 'check_load',
                         NagiosProperties.STATUS: NagiosTestStatus.CRITICAL,
                         NagiosProperties.LAST_CHECK: '2016-02-16 14:27:06',
                         NagiosProperties.DURATION: ' 1d  0h 54m 59s',
                         NagiosProperties.ATTEMPT: '1/1',
                         NagiosProperties.STATUS_INFO:
                             'Critical Error\xa0'}

    expected_service3 = {NagiosProperties.RESOURCE_NAME: 'compute-0-0.local',
                         NagiosProperties.SERVICE: 'Disk IO SUMMARY',
                         NagiosProperties.STATUS: NagiosTestStatus.OK,
                         NagiosProperties.LAST_CHECK: '2016-02-17 15:21:22',
                         NagiosProperties.DURATION: '14d  1h 28m 34s',
                         NagiosProperties.ATTEMPT: '1/1',
                         NagiosProperties.STATUS_INFO:
                             'OK - 0.00 B/sec read, 1.84 MB/sec write, '
                             'IOs: 89.00/sec\xa0'}

    # noinspection PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(NagiosParserTest, cls).setUpClass()

    def test_template_loader(self):
        # Setup
        fp = open(utils.get_resources_dir() + '/nagios/nagios-mock.html')
        nagios_html = fp.read()

        # Action
        nagios_services = NagiosParser().parse(nagios_html)

        # Test assertions
        self.assertTrue(nagios_services)
        self._assert_contains(self.expected_service1, nagios_services)
        self._assert_contains(self.expected_service2, nagios_services)
        self._assert_contains(self.expected_service3, nagios_services)
