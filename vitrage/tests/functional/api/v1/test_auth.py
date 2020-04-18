# Copyright 2017 - Nokia Corporation
# Copyright 2014 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# noinspection PyPackageRequirements
from datetime import datetime
from unittest import mock
import uuid


from keystonemiddleware import fixture as ksm_fixture
# noinspection PyPackageRequirements
from vitrage.tests.functional.api.v1 import FunctionalTest

EVENT_DETAILS = {
    'hostname': 'host123',
    'source': 'sample_monitor',
    'cause': 'another alarm',
    'severity': 'critical',
    'status': 'down',
    'monitor_id': 'sample monitor',
    'monitor_event_id': '456',
}

VALID_TOKEN = uuid.uuid4().hex

HEADERS = {
    'X-Auth-Token': VALID_TOKEN,
    'X-Project-Id': 'admin',
    'X-Roles': 'admin'
}


class AuthTest(FunctionalTest):

    def __init__(self, *args, **kwds):
        super(AuthTest, self).__init__(*args, **kwds)
        self.auth = 'keystone'

    def setUp(self):
        super(AuthTest, self).setUp()
        self.auth_token_fixture = self.useFixture(
            ksm_fixture.AuthTokenFixture())
        self.auth_token_fixture.add_token_data(
            token_id=VALID_TOKEN,
            project_id='admin',
            role_list=['admin'],
            user_name='user_name',
            user_id='user_id',
            is_v2=True
        )

    def test_in_keystone_mode_not_authenticated(self):
        resp = self.post_json('/topology/', params=None, expect_errors=True)
        self.assertEqual('401 Unauthorized', resp.status)

    def test_in_keystone_mode_auth_success(self):
        with mock.patch('pecan.request') as request:
            resp = self.post_json('/event/',
                                  params={
                                      'time': datetime.now().isoformat(),
                                      'type': 'compute.host.down',
                                      'details': EVENT_DETAILS
                                  },
                                  headers=HEADERS)

            self.assertEqual(1, request.client.call.call_count)
            self.assertEqual('200 OK', resp.status)
