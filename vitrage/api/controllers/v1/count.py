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

import json
import pecan

from oslo_log import log
from oslo_utils.strutils import bool_from_string
from pecan.core import abort

from vitrage.api.controllers.rest import RootRestController
from vitrage.api.policy import enforce


LOG = log.getLogger(__name__)


# noinspection PyBroadException
class AlarmCountsController(RootRestController):

    @pecan.expose('json')
    def index(self, all_tenants=False):
        return self.get(all_tenants)

    @pecan.expose('json')
    def get(self, all_tenants=False):
        all_tenants = bool_from_string(all_tenants)
        if all_tenants:
            enforce("get alarms count:all_tenants", pecan.request.headers,
                    pecan.request.enforcer, {})
        else:
            enforce("get alarms count", pecan.request.headers,
                    pecan.request.enforcer, {})

        LOG.info('received get alarm counts')

        try:
            alarm_counts_json = pecan.request.client.call(
                pecan.request.context, 'get_alarm_counts',
                all_tenants=all_tenants)

            return json.loads(alarm_counts_json)

        except Exception:
            LOG.exception('failed to get alarm count.')
            abort(404, 'Failed to get alarm count.')


class ResourceCountsController(RootRestController):

    @pecan.expose('json')
    def post(self, **kwargs):
        resource_type = kwargs.get('resource_type', None)
        all_tenants = kwargs.get('all_tenants', False)
        all_tenants = bool_from_string(all_tenants)
        query = kwargs.get('query')
        group_by = kwargs.get('group_by')
        if query:
            query = json.loads(query)

        if all_tenants:
            enforce("count resources:all_tenants", pecan.request.headers,
                    pecan.request.enforcer, {})
        else:
            enforce("count resources", pecan.request.headers,
                    pecan.request.enforcer, {})

        LOG.info('received get resource counts')

        try:
            resource_counts_json = pecan.request.client.call(
                pecan.request.context, 'count_resources',
                resource_type=resource_type,
                all_tenants=all_tenants,
                query=query,
                group_by=group_by)

            return json.loads(resource_counts_json)

        except Exception:
            LOG.exception('failed to get resource count.')
            abort(404, 'Failed to get resource count.')
