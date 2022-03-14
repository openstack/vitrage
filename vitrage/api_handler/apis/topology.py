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
from networkx.algorithms.shortest_paths.generic import shortest_path
from networkx import is_frozen

from oslo_log import log
from osprofiler import profiler

from vitrage.api_handler.apis import base
from vitrage.common.constants import EdgeProperties as EProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import TenantProps
from vitrage.common.constants import VertexProperties as VProps
from vitrage.common.exception import VitrageError
from vitrage.common.utils import compress_obj
from vitrage.common.utils import timed_method
from vitrage.datasources import OPENSTACK_CLUSTER

LOG = log.getLogger(__name__)


@profiler.trace_cls("topology apis",
                    info={}, hide_args=False, trace_private=False)
class TopologyApis(base.EntityGraphApisBase):

    @timed_method(log_results=True)
    @base.lock_graph
    def get_topology(self, ctx, graph_type, depth, query, root, all_tenants):
        LOG.debug("TopologyApis get_topology - root: %s, all_tenants=%s",
                  root, all_tenants)

        project_id = ctx.get(TenantProps.PROJECT_ID, None)
        is_admin_project = ctx.get(TenantProps.IS_ADMIN, False)

        LOG.debug('project_id = %s, is_admin_project  %s',
                  project_id, is_admin_project)

        root_id = root or self._default_root_id()
        if graph_type == 'tree' or \
                ((root is not None) and (depth is not None)):
            if not query:
                LOG.error("Graph-type 'tree' requires a filter.")
                raise Exception("Graph-type 'tree' requires a filter.")

            current_query = query
            if not all_tenants:
                project_query = \
                    {'or': [{'==': {VProps.PROJECT_ID: project_id}},
                            {'==': {VProps.PROJECT_ID: None}}]}
                current_query = {'and': [query, project_query]}

            graph = self.entity_graph.algo.graph_query_vertices(
                root_id,
                query_dict=current_query,
                depth=depth,
                edge_query_dict=base.EDGE_QUERY)
        # By default the graph_type is 'graph'
        else:
            if all_tenants:
                q = query if query else base.TOPOLOGY_AND_ALARMS_QUERY
                graph = \
                    self.entity_graph.algo.create_graph_from_matching_vertices(
                        query_dict=q,
                        edge_attr_filter={VProps.VITRAGE_IS_DELETED: False})
            else:
                graph = self._get_topology_for_specific_project(
                    query,
                    project_id,
                    is_admin_project,
                    root_id)

        data = graph.json_output_graph(raw=True)
        return compress_obj(data, level=1)

    def _get_topology_for_specific_project(self,
                                           query,
                                           project_id,
                                           is_admin_project,
                                           root):
        """Finds the topology in consideration with the project_id

        Finds all the entities which has project_id. In case the tenant is
        admin then project_id can also be None.

        :type query: dictionary
        :type project_id: string
        :type is_admin_project: boolean
        :type root: string
        :rtype: NXGraph
        """

        if query:
            q = self._add_project_to_query(query, project_id, is_admin_project)
        else:
            alarm_query = self._get_query_with_project(EntityCategory.ALARM,
                                                       project_id,
                                                       is_admin=True)

            resource_query = \
                self._get_query_with_project(EntityCategory.RESOURCE,
                                             project_id,
                                             is_admin_project)

            default_query = {'or': [resource_query, alarm_query]}
            q = default_query

        vertices_ids = self.entity_graph.get_vertices_ids(query_dict=q)
        vertices_ids = self._all_paths_from_node(self.entity_graph,
                                                 source_node=root,
                                                 targets=vertices_ids)
        graph = self.entity_graph.algo.subgraph(vertices_ids)
        edge_query = {EProps.VITRAGE_IS_DELETED: False}
        self._remove_unnecessary_elements(
            graph, project_id, is_admin_project, edge_attr_filter=edge_query)

        return graph

    def _remove_unnecessary_elements(self,
                                     graph,
                                     project_id,
                                     is_admin_project,
                                     edge_attr_filter):
        # delete non matching edges
        self.entity_graph.algo.apply_edge_attr_filter(graph, edge_attr_filter)

        self._remove_alarms_of_other_projects(graph,
                                              project_id,
                                              is_admin_project)

    def _remove_alarms_of_other_projects(self,
                                         graph,
                                         current_project_id,
                                         is_admin_project):
        """Removes wrong alarms from the graph

        Removes alarms of other tenants from the graph, In case the tenant is
        admin then project_id can also be None.

        :type graph: NXGraph
        :type current_project_id: string
        :type is_admin_project: boolean
        """
        alarms_to_remove = []
        for alarm in graph.get_vertices(query_dict=base.ALARMS_ALL_QUERY):
            if not alarm.get(VProps.PROJECT_ID, None):
                cat_filter = {VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE}
                resource_neighbors = \
                    self.entity_graph.neighbors(alarm.vertex_id,
                                                vertex_attr_filter=cat_filter)
                if len(resource_neighbors) > 0:
                    resource_proj_id = \
                        resource_neighbors[0].get(VProps.PROJECT_ID, None)
                    cond1 = is_admin_project and resource_proj_id and \
                        resource_proj_id != current_project_id
                    cond2 = not is_admin_project and \
                        (not resource_proj_id or
                         resource_proj_id != current_project_id)
                    if cond1 or cond2:
                        alarms_to_remove.append(alarm)

        if alarms_to_remove and is_frozen(graph._g):
            graph._g = graph._g.copy()

        for alarm in alarms_to_remove:
            graph.remove_vertex(alarm)

    @staticmethod
    def _all_paths_from_node(graph, source_node, targets):
        """Find all nodes on a (shortest) path from source to targets

        Return all the node ids that are either in targets
        or are in a path from source node to any of targets

        :rtype: list
        """
        vertices_ids = targets
        paths = shortest_path(graph._g, source=source_node)
        vertices_ids.update(*[set(paths.get(n, [])) for n in targets])
        return vertices_ids

    def _default_root_id(self):
        tmp_vertices = self.entity_graph.get_vertices(
            vertex_attr_filter={VProps.VITRAGE_TYPE: OPENSTACK_CLUSTER})
        if not tmp_vertices:
            LOG.debug("No root vertex found")
            return None
        if len(tmp_vertices) > 1:
            raise VitrageError("Multiple root vertices found")
        return tmp_vertices[0].vertex_id
