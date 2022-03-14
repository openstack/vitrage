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

    @timed_method(log_results=True)
    @base.lock_graph
    def get_resources(self, ctx, resource_type=None, all_tenants=False,
                      query=None):
        LOG.debug(
            'ResourceApis get_resources - resource_type: %s, all_tenants: %s,'
            ' query: %s',
            resource_type,
            all_tenants,
            query)

        query = self._get_query(ctx, resource_type, all_tenants, query)
        resources = self.entity_graph.get_vertices(query_dict=query)
        data = {'resources': [r.properties for r in resources]}
        return compress_obj(data, level=1)

    @timed_method(log_results=True)
    @base.lock_graph
    def count_resources(self, ctx, resource_type=None, all_tenants=False,
                        query=None, group_by=None):
        LOG.debug(
            'ResourceApis count_resources - type: %s, all_tenants: %s,'
            ' query: %s, group_by: %s',
            resource_type,
            all_tenants,
            query,
            group_by)

        query = self._get_query(ctx, resource_type, all_tenants, query)
        if group_by is None:
            group_by = VProps.VITRAGE_TYPE
        counts = self.entity_graph.get_vertices_count(query_dict=query,
                                                      group_by=group_by)

        return json.dumps(counts)

    def _get_query(self, ctx, resource_type, all_tenants, query_dict):
        project_id = ctx.get(TenantProps.PROJECT_ID, None)
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

        if query_dict:
            query['and'].append(query_dict)
        return query

    @base.lock_graph
    def show_resource(self, ctx, vitrage_id):

        LOG.debug('Show resource with vitrage_id: %s', vitrage_id)
        resource = self.entity_graph.get_vertex(vitrage_id)
        if not resource or resource.get(VProps.VITRAGE_CATEGORY) != \
                EntityCategory.RESOURCE:
            LOG.warning('Resource show - Not found (%s)', vitrage_id)
            return None

        is_admin = ctx.get(TenantProps.IS_ADMIN, False)
        curr_project = ctx.get(TenantProps.PROJECT_ID, None)
        resource_project = resource.get(VProps.PROJECT_ID)
        if not is_admin and curr_project != resource_project:
            LOG.warning('Resource show - Authorization failed (%s)',
                        vitrage_id)
            return None

        return json.dumps(resource.properties)
