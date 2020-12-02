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

from unittest import mock

from vitrage.api_handler.apis.template import TemplateApis
from vitrage.evaluator import init_template_schemas
from vitrage.tests.functional.api.v1 import FunctionalTest


VERSIONS = [
    {
        'version': 'v1',
        'status': 'SUPPORTED'
    },
    {
        'version': 'v2',
        'status': 'SUPPORTED'
    },
    {
        'version': 'v3',
        'status': 'CURRENT'
    }
]


class TemplateVersionsTest(FunctionalTest):
    def __init__(self, *args, **kwds):
        super(TemplateVersionsTest, self).__init__(*args, **kwds)
        self.auth = 'noauth'
        init_template_schemas()

    def test_get_versions(self):
        with mock.patch('pecan.request') as request:
            versions = TemplateApis().template_versions(mock.Mock())
            request.client.call.return_value = versions
            resp = self.get_json('/template/versions/')
            self.assert_list_equal(VERSIONS, resp)
