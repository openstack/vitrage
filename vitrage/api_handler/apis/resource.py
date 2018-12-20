# Copyright 2016 - ZTE, Nokia
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
import copy
import json
from oslo_log import log
from osprofiler import profiler

from vitrage.api_handler.apis import base
from vitrage.api_handler.apis.base import RESOURCES_ALL_QUERY
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import TenantProps
from vitrage.common.constants import VertexProperties as VProps
from vitrage.common.utils import compress_obj
from vitrage.common.utils import timed_method

LOG = log.getLogger(__name__)


@profiler.trace_cls("resource apis",
                    info={}, hide_args=False, trace_private=False)
class ResourceApis(base.EntityGraphApisBase):

    def __init__(self, entity_graph, conf, api_lock):
        super(ResourceApis, self).__init__(entity_graph, conf, api_lock)

    @timed_method(log_results=True)
    @base.lock_graph
    def get_resources(self, ctx, resource_type=None, all_tenants=False):
        LOG.debug('ResourceApis get_resources - resource_type: %s,'
                  'all_tenants: %s', str(resource_type), all_tenants)

        project_id = ctx.get(TenantProps.TENANT, None)
        is_admin_project = ctx.get(TenantProps.IS_ADMIN, False)

        if all_tenants:
            resource_query = RESOURCES_ALL_QUERY
        else:
            resource_query = self._get_query_with_project(
                EntityCategory.RESOURCE,
                project_id,
                is_admin_project)
        query = copy.deepcopy(resource_query)

        if resource_type:
            type_query = {'==': {VProps.VITRAGE_TYPE: resource_type}}
            query['and'].append(type_query)

        resources = self.entity_graph.get_vertices(query_dict=query)
        data = {'resources': [r.properties for r in resources]}
        return compress_obj(data, level=1)

    @base.lock_graph
    def show_resource(self, ctx, vitrage_id):

        LOG.debug('Show resource with vitrage_id: %s', vitrage_id)
        resource = self.entity_graph.get_vertex(vitrage_id)
        if not resource or resource.get(VProps.VITRAGE_CATEGORY) != \
                EntityCategory.RESOURCE:
            LOG.warning('Resource show - Not found (%s)', vitrage_id)
            return None

        is_admin = ctx.get(TenantProps.IS_ADMIN, False)
        curr_project = ctx.get(TenantProps.TENANT, None)
        resource_project = resource.get(VProps.PROJECT_ID)
        if not is_admin and curr_project != resource_project:
            LOG.warning('Resource show - Authorization failed (%s)',
                        vitrage_id)
            return None

        return json.dumps(resource.properties)
