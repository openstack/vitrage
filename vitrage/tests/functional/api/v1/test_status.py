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

from unittest import mock

import oslo_messaging


from vitrage.tests.functional.api.v1 import FunctionalTest


class StatusTest(FunctionalTest):
    def __init__(self, *args, **kwds):
        super(StatusTest, self).__init__(*args, **kwds)
        self.auth = 'noauth'

    def test_get_status_ok(self):
        with mock.patch('pecan.request') as request:
            client = mock.Mock()
            client.call.return_value = True
            request.client.prepare.return_value = client
            resp = self.get_json('/status/')
            self.assert_dict_equal({'reason': 'OK'}, resp)

    def test_get_status_not_ok(self):
        with mock.patch('pecan.request') as request:
            client = mock.Mock()
            client.call.return_value = False
            request.client.prepare.return_value = client
            resp = self.get_json('/status/', expect_errors=True)
            self.assertEqual(503, resp.status_code)
            self.assertIn('vitrage-graph is not ready', resp.text)

    def test_get_status_not_ok_timeout(self):
        with mock.patch('pecan.request') as request:
            client = mock.Mock()
            client.call.side_effect = oslo_messaging.MessagingTimeout()
            request.client.prepare.return_value = client
            resp = self.get_json('/status/', expect_errors=True)
            self.assertEqual(503, resp.status_code)
            self.assertIn('vitrage-graph is not available', resp.text)
