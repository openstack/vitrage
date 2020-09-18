# Copyright 2018 - Nokia Corporation
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
from unittest import mock
import uuid

from datetime import datetime
# noinspection PyPackageRequirements
from http import client as httplib
from vitrage.tests.functional.api.v1 import FunctionalTest

HEADERS = {
    'Authorization': 'Basic dml0cmFnZTpwYXNzd29yZA==',
    'User-Agent': 'Alertmanager/0.15.0',
    'Host': '127.0.0.1:8999',
    'Content-Type': 'application/json'
}

EVENT_TYPE = 'prometheus.alarm'

VALID_TOKEN = uuid.uuid4().hex

PROJECT_ID = 'best_project'


class Role(object):
    pass


ROLES = Role()

ROLES.role_names = ['admin']

EVENT_DETAILS = {
    "status": "firing",
    "groupLabels": {
        "alertname": "HighInodeUsage"
    },
    "groupKey": "{}:{alertname=\"HighInodeUsage\"}",
    "commonAnnotations": {
        "mount_point": "/%",
        "description": "\"Consider ssh\"ing into the instance \"\n",
        "title": "High number of inode usage",
        "value": "96.81%",
        "device": "/dev/vda1%",
        "runbook": "troubleshooting/filesystem_alerts_inodes.md"
    },
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "severity": "critical",
                "fstype": "ext4",
                "instance": "localhost:9100",
                "job": "node",
                "alertname": "HighInodeUsage",
                "device": "/dev/vda1",
                "mountpoint": "/"
            },
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://devstack-rocky-4:9090/graph?g0.htm1",
            "startsAt": "2018-05-03T12:25:38.231388525Z",
            "annotations": {
                "mount_point": "/%",
                "description": "\"Consider ssh\"ing into the instance\"\n",
                "title": "High number of inode usage",
                "value": "96.81%",
                "device": "/dev/vda1%",
                "runbook": "troubleshooting/filesystem_alerts_inodes.md"
            }
        }
    ],
    "version": "4",
    "receiver": "vitrage",
    "externalURL": "http://devstack-rocky-4:9093",
    "commonLabels": {
        "severity": "critical",
        "fstype": "ext4",
        "instance": "localhost:9100",
        "job": "node",
        "alertname": "HighInodeUsage",
        "device": "/dev/vda1",
        "mountpoint": "/"
    }
}

ERR_MSG_MISSING_AUTH = 'The request you have made requires authentication.'

ERR_MSG_MISSING_VERSIONED_IDENTITY_ENDPOINTS = 'Authorization exception: ' \
                                               'Could not find versioned ' \
                                               'identity endpoints when ' \
                                               'attempting to authenticate. ' \
                                               'Please check that your ' \
                                               'auth_url is correct.'

ERR_MISSING_AUTH = {'error': {
    'code': httplib.UNAUTHORIZED,
    'title': httplib.responses[httplib.UNAUTHORIZED],
    'message': ERR_MSG_MISSING_AUTH,
}}

ERR_MISSING_VERSIONED_IDENTITY_ENDPOINTS = {'error': {
    'code': httplib.UNAUTHORIZED,
    'title': httplib.responses[httplib.UNAUTHORIZED],
    'message': ERR_MSG_MISSING_VERSIONED_IDENTITY_ENDPOINTS,
}}


class BasicAuthTest(FunctionalTest):

    def __init__(self, *args, **kwds):
        super(BasicAuthTest, self).__init__(*args, **kwds)
        self.auth = 'keystone'

    keystoneauth__identity = 'keystoneauth1.identity'

    @mock.patch('keystoneauth1.session.Session.get_token',
                return_value=VALID_TOKEN)
    @mock.patch('%s.base.BaseIdentityPlugin.get_project_id' %
                keystoneauth__identity,
                return_value=PROJECT_ID)
    @mock.patch('%s.generic.base.BaseGenericPlugin.get_auth_ref' %
                keystoneauth__identity,
                return_value=ROLES)
    @mock.patch('pecan.request')
    def test_header_parsing(self, req_mock, *args):
        resp = self.post_json('/event',
                              params={
                                  'time': datetime.now().isoformat(),
                                  'type': EVENT_TYPE,
                                  'details': EVENT_DETAILS
                              },
                              headers=HEADERS)
        req = resp.request
        self.assertEqual('Confirmed', req.headers['X-Identity-Status'])
        self.assertEqual(ROLES.role_names[0], req.headers['X-Roles'])
        self.assertEqual(PROJECT_ID, req.headers['X-Project-Id'])
        self.assertEqual(VALID_TOKEN, req.headers['X-Auth-Token'])
        self.assertEqual(1, req_mock.client.call.call_count)

    @mock.patch('keystoneauth1.session.Session.request')
    def test_basic_mode_auth_wrong_authorization(self, *args):
        wrong_headers = HEADERS.copy()
        wrong_headers['Authorization'] = 'Basic dml0cmFnZTpwdml0cmFnZT=='
        resp = self.post_json('/event',
                              params={
                                  'time': datetime.now().isoformat(),
                                  'type': EVENT_TYPE,
                                  'details': EVENT_DETAILS
                              },
                              headers=wrong_headers,
                              expect_errors=True)
        self.assertEqual(httplib.UNAUTHORIZED, resp.status_code)
        self.assertDictEqual(ERR_MISSING_VERSIONED_IDENTITY_ENDPOINTS,
                             resp.json)

    def test_in_basic_mode_auth_no_header(self):
        resp = self.post_json('/event', expect_errors=True)

        self.assertEqual(httplib.UNAUTHORIZED, resp.status_code)
        self.assertDictEqual(ERR_MISSING_AUTH, resp.json)

    @mock.patch('keystoneauth1.identity.generic.password.Password')
    @mock.patch('keystoneauth1.session.Session')
    @mock.patch('pecan.request')
    def test_in_basic_mode_auth_success(self, req_mock, *args):
        resp = self.post_json('/event',
                              params={
                                  'time': datetime.now().isoformat(),
                                  'type': EVENT_TYPE,
                                  'details': EVENT_DETAILS
                              },
                              headers=HEADERS)

        self.assertEqual(1, req_mock.client.call.call_count)
        self.assertEqual(httplib.OK, resp.status_code)
