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
from oslo_log import versionutils
from oslo_utils.strutils import bool_from_string
from osprofiler import profiler
from pecan.core import abort

from vitrage.api.controllers.rest import RootRestController
from vitrage.api.controllers.v1 import count
from vitrage.api.policy import enforce
from vitrage.common.utils import decompress_obj

LOG = log.getLogger(__name__)


# noinspection PyBroadException
@profiler.trace_cls("resource controller",
                    info={}, hide_args=False, trace_private=False)
class ResourcesController(RootRestController):
    count = count.ResourceCountsController()

    @pecan.expose('json')
    def post(self, **kwargs):
        LOG.info('post list resource with args: %s', kwargs)

        resource_type = kwargs.get('resource_type', None)
        all_tenants = kwargs.get('all_tenants', False)
        all_tenants = bool_from_string(all_tenants)
        query = kwargs.get('query')
        try:
            return self._get_resources(resource_type, all_tenants, query)
        except Exception:
            LOG.exception('Failed to list resources.')
            abort(404, 'Failed to list resources.')

    @pecan.expose('json')
    @versionutils.deprecated(
        as_of=versionutils.deprecated.STEIN,
        what='rca:list_resources GET',
        in_favor_of='rca:list_resources POST',
    )
    def get_all(self, **kwargs):
        LOG.info('get list resource with args: %s', kwargs)

        resource_type = kwargs.get('resource_type', None)
        all_tenants = kwargs.get('all_tenants', False)
        all_tenants = bool_from_string(all_tenants)
        query = kwargs.get('query')

        try:
            return self._get_resources(resource_type, all_tenants, query)
        except Exception:
            LOG.exception('Failed to list resources.')
            abort(404, 'Failed to list resources.')

    @staticmethod
    def _get_resources(resource_type=None, all_tenants=False, query=None):
        if query:
            query = json.loads(query)

        if all_tenants:
            enforce('list resources:all_tenants', pecan.request.headers,
                    pecan.request.enforcer, {})
        else:
            enforce('list resources', pecan.request.headers,
                    pecan.request.enforcer, {})

        LOG.info('get resources with type: %s, all_tenants: %s, query: %s',
                 resource_type, all_tenants, query)

        resources = pecan.request.client.call(
            pecan.request.context,
            'get_resources',
            resource_type=resource_type,
            all_tenants=all_tenants,
            query=query)
        resources = decompress_obj(resources)['resources']
        return resources

    @pecan.expose('json')
    def get(self, vitrage_id):

        LOG.info('get resource show with vitrage_id: %s', vitrage_id)

        enforce("get resource",
                pecan.request.headers,
                pecan.request.enforcer,
                {})

        return self._show_resource(vitrage_id)

    @staticmethod
    def _show_resource(vitrage_id):
        try:
            resource = pecan.request.client.call(
                pecan.request.context,
                'show_resource',
                vitrage_id=vitrage_id)
            if not resource:
                abort(404, "Failed to find resource %s" % vitrage_id)

            LOG.debug('resource found = %s', resource)

            return json.loads(resource)
        except Exception:
            LOG.exception('failed to show resource with vitrage_id(%s).',
                          vitrage_id)
            abort(404, 'Failed to show resource.')
