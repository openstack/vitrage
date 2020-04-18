# Copyright 2016 - Nokia Corporation
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


from datetime import datetime
# noinspection PyPackageRequirements
from unittest import mock
from vitrage.common.utils import compress_obj

from vitrage.storage.sqlalchemy import models
from vitrage.tests.functional.api.v1 import FunctionalTest


class NoAuthTest(FunctionalTest):

    def __init__(self, *args, **kwds):
        super(NoAuthTest, self).__init__(*args, **kwds)
        self.auth = 'noauth'

    def test_noauth_mode_post_event(self):

        with mock.patch('pecan.request') as request:

            details = {
                'hostname': 'host123',
                'source': 'sample_monitor',
                'cause': 'another alarm',
                'severity': 'critical',
                'status': 'down',
                'monitor_id': 'sample monitor',
                'monitor_event_id': '456',
            }
            event_time = datetime.now().isoformat()
            event_type = 'compute.host.down'

            resp = self.post_json('/event/', params={'time': event_time,
                                                     'type': event_type,
                                                     'details': details})

            self.assertEqual(1, request.client.call.call_count)
            self.assertEqual('200 OK', resp.status)

    def test_noauth_mode_get_topology(self):
        with mock.patch('pecan.request') as request:
            request.client.call.return_value = compress_obj({})
            params = dict(depth=None, graph_type='graph', query=None,
                          root=None,
                          all_tenants=False)
            resp = self.post_json('/topology/', params=params)

            self.assertEqual(1, request.client.call.call_count)
            self.assertEqual('200 OK', resp.status)
            self.assert_is_empty(resp.json)

    def test_noauth_mode_list_alarms(self):
        with mock.patch('pecan.request') as request:
            request.client.call.return_value = compress_obj({"alarms": []})
            params = dict(vitrage_id='all', all_tenants=False)
            data = self.get_json('/alarm/', params=params)

            self.assertEqual(1, request.client.call.call_count)
            self.assert_is_empty(data)

    def test_noauth_mode_show_alarm(self):

        with mock.patch('pecan.request') as request:
            request.client.call.return_value = '{}'
            data = self.get_json('/alarm/1234')

            self.assertEqual(1, request.client.call.call_count)
            self.assert_is_empty(data)

    def test_noauth_mode_show_alarm_count(self):
        with mock.patch('pecan.request') as request:
            request.client.call.return_value = '{}'
            params = dict(all_tenants=False)
            resp = self.post_json('/alarm/count/', params=params)

            self.assertEqual(1, request.client.call.call_count)
            self.assertEqual('200 OK', resp.status)
            self.assert_is_empty(resp.json)

    def test_noauth_mode_list_resources(self):

        with mock.patch('pecan.request') as request:
            request.client.call.return_value = compress_obj({"resources": []})
            params = dict(resource_type='all', all_tenants=False)
            data = self.get_json('/resources/', params=params)

            self.assertEqual(1, request.client.call.call_count)
            self.assert_is_empty(data)

    def test_noauth_mode_show_resource(self):

        with mock.patch('pecan.request') as request:
            request.client.call.return_value = '{}'
            data = self.get_json('/resources/1234')

            self.assertEqual(1, request.client.call.call_count)
            self.assert_is_empty(data)

    def test_noauth_mode_list_templates(self):

        with mock.patch('pecan.request') as request:
            request.storage.templates.query.return_value = []
            data = self.get_json('/template/')

            self.assertEqual(1, request.storage.templates.query.call_count)
            self.assert_is_empty(data)

    def test_noauth_mode_show_template(self):

        with mock.patch('pecan.request') as request:
            request.storage.templates.query.return_value = \
                [models.Template(file_content={})]
            data = self.get_json('/template/1234')

            self.assertEqual(1, request.storage.templates.query.call_count)
            self.assertEqual(
                1, request.storage.templates.query_with_status_not.call_count)
            self.assert_is_empty(data)

    def test_noauth_mode_validate_template(self):

        with mock.patch('pecan.request') as request:
            request.client.call.return_value = '{}'
            params = {"templates": {}}
            resp = self.post_json('/template/', params=params)

            self.assertEqual(1, request.client.call.call_count)
            self.assertEqual('200 OK', resp.status)
            self.assert_is_empty(resp.json)

    def test_noauth_mode_get_rca(self):

        with mock.patch('pecan.request') as request:
            request.client.call.return_value = '{}'
            params = dict(all_tenants=False)
            data = self.get_json('/rca/1234/', params=params)

            self.assertEqual(1, request.client.call.call_count)
            self.assert_is_empty(data)
