#  Copyright 2019 - Nokia Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from datetime import datetime
import os
import socket
from unittest import mock

# noinspection PyPackageRequirements
from iso8601.iso8601 import UTC
# noinspection PyPackageRequirements
from oslo_utils import timeutils
# noinspection PyPackageRequirements
import webtest

from vitrage.api import app
from vitrage.coordination.coordination import Coordinator
from vitrage.tests.functional.api.v1 import FunctionalTest


class ServiceTest(FunctionalTest):

    SERVICE_CREATION_TIME = datetime(2015, 1, 26, 12, 57, 4, tzinfo=UTC)

    def __init__(self, *args, **kwds):
        super(ServiceTest, self).__init__(*args, **kwds)
        self.auth = 'noauth'

    def test_get_services_no_backend(self):
        resp = self.get_json('/service/', expect_errors=True)
        self.assertEqual(500, resp.status_code)
        self.assertIn('Service API not supported', resp.text)

    def test_get_services_no_connection_to_backend(self):
        self._use_zake_as_backend()
        with mock.patch('pecan.request') as request:
            request.coordinator.is_active.return_value = False
            resp = self.get_json('/service/', expect_errors=True)

            self.assertEqual(500, resp.status_code)
            self.assertIn('Failed to connect to coordination backend',
                          resp.text)

    @mock.patch.object(timeutils, 'utcnow')
    def test_get_services(self, utcnow):
        now = self._mock_service_creation_time(utcnow)

        # NOTE(eyalb) we want to force coordinator to be initialized with a
        # custom name otherwise it will take the command line string as a name
        name = 'vitrage'

        def mock_coordinator():
            return Coordinator(name)

        with mock.patch('vitrage.coordination.coordination.Coordinator',
                        new=mock_coordinator):
            self._use_zake_as_backend()

            data = self.get_json('/service/')

            self.assert_list_equal([
                {
                    'name': name,
                    'hostname': socket.gethostname(),
                    'process': os.getpid(),
                    'created': now
                }
            ], data)

    def _mock_service_creation_time(self, utcnow):
        utcnow.return_value = self.SERVICE_CREATION_TIME
        return utcnow.return_value.isoformat()

    # noinspection PyAttributeOutsideInit
    def _use_zake_as_backend(self):
        self.conf.set_override('backend_url', 'zake://', 'coordination')

        self.app = webtest.TestApp(app.load_app())
