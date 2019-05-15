# Copyright 2016 - Nokia
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
import functools
from oslo_log import log

from vitrage.common.constants import EdgeProperties as EProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.nova.zone import NOVA_ZONE_DATASOURCE
from vitrage.datasources import OPENSTACK_CLUSTER

LOG = log.getLogger(__name__)


# Used for Sunburst to show only specific resources
TREE_TOPOLOGY_QUERY = {
    'and': [
        {'==': {VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE}},
        {'==': {VProps.VITRAGE_IS_DELETED: False}},
        {'==': {VProps.VITRAGE_IS_PLACEHOLDER: False}},
        {
            'or': [
                {'==': {VProps.VITRAGE_TYPE: OPENSTACK_CLUSTER}},
                {'==': {VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE}},
                {'==': {VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE}},
                {'==': {VProps.VITRAGE_TYPE: NOVA_ZONE_DATASOURCE}}
            ]
        }
    ]
}

TOPOLOGY_AND_ALARMS_QUERY = {
    'and': [
        {'==': {VProps.VITRAGE_IS_DELETED: False}},
        {'==': {VProps.VITRAGE_IS_PLACEHOLDER: False}},
        {
            'or': [
                {'==': {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM}},
                {'==': {VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE}}
            ]
        }
    ]
}


ALARMS_ALL_QUERY = {
    'and': [
        {'==': {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM}},
        {'==': {VProps.VITRAGE_IS_DELETED: False}}
    ]
}

EDGE_QUERY = {'==': {EProps.VITRAGE_IS_DELETED: False}}

RESOURCES_ALL_QUERY = {
    'and': [
        {'==': {VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE}},
        {'==': {VProps.VITRAGE_IS_DELETED: False}},
        {'==': {VProps.VITRAGE_IS_PLACEHOLDER: False}}
    ]
}


class EntityGraphApisBase(object):

    def __init__(self, entity_graph, api_lock, db=None):
        self.entity_graph = entity_graph
        self.db = db
        self.api_lock = api_lock

    @classmethod
    def _get_query_with_project(cls, vitrage_category, project_id, is_admin):
        """Generate query with tenant data

        Creates query for entity graph which takes into consideration the
        vitrage_category, project_id and if the tenant is admin

        :type vitrage_category: string
        :type project_id: string
        :type is_admin: boolean
        :rtype: dictionary
        """

        query = {
            'and': [
                {'==': {VProps.VITRAGE_IS_DELETED: False}},
                {'==': {VProps.VITRAGE_IS_PLACEHOLDER: False}},
                {'==': {VProps.VITRAGE_CATEGORY: vitrage_category}}
            ]
        }

        cls._add_project_to_query(query, project_id, is_admin)

        return query

    @staticmethod
    def _add_project_to_query(query, project_id, is_admin):
        """Add project_id filter to the query

        Each query should contain the project_id condition

        :type query: string representing a json query
        :type project_id: string
        :type is_admin: boolean
        :rtype: string representing a json query
        """

        if is_admin:
            project_query = \
                {'or': [{'==': {VProps.PROJECT_ID: project_id}},
                        {'==': {VProps.PROJECT_ID: None}}]}
        else:
            project_query = \
                {'==': {VProps.PROJECT_ID: project_id}}

        if 'and' in query:
            query_with_project_id = query
            query_with_project_id['and'].append(project_query)
        else:
            query_with_project_id = {'and': [project_query, query]}

        return query_with_project_id


def lock_graph(f):
    @functools.wraps(f)
    def api_backend_func(*args, **kwargs):
        try:
            args[0].api_lock.acquire()
            result = f(*args, **kwargs)
            return result
        finally:
            args[0].api_lock.release()
    return api_backend_func
