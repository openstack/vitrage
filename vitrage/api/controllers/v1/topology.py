# Copyright 2016 - Alcatel-Lucent
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

import json
import networkx as nx
from networkx.readwrite import json_graph

from oslo_log import log
from oslo_utils.strutils import bool_from_string
from osprofiler import profiler
import pecan
from pecan.core import abort

from vitrage.api.controllers.rest import RootRestController
from vitrage.api.policy import enforce
from vitrage.common.constants import VertexProperties as VProps
from vitrage.common.utils import to_int

# noinspection PyProtectedMember
from vitrage.common.utils import decompress_obj
from vitrage.datasources import OPENSTACK_CLUSTER
from vitrage.datasources.transformer_base import CLUSTER_ID


LOG = log.getLogger(__name__)


# noinspection PyBroadException
@profiler.trace_cls("topology controller",
                    info={}, hide_args=False, trace_private=False)
class TopologyController(RootRestController):

    @pecan.expose('json')
    def post(self, depth=None, graph_type='graph', query=None, root=None,
             all_tenants=False):
        all_tenants = bool_from_string(all_tenants)
        depth = to_int(depth)
        if all_tenants:
            enforce('get topology:all_tenants', pecan.request.headers,
                    pecan.request.enforcer, {})
        else:
            enforce("get topology", pecan.request.headers,
                    pecan.request.enforcer, {})

        LOG.info('received get topology: depth->%(depth)s '
                 'graph_type->%(graph_type)s root->%(root)s '
                 'all_tenants-->%(all_tenants)s',
                 {'depth': depth, 'graph_type': graph_type, 'root': root,
                  'all_tenants': all_tenants})

        if query:
            query = json.loads(query)
            LOG.info("query is %s", query)

        return self.get_graph(graph_type, depth, query, root, all_tenants)

    @staticmethod
    def get_graph(graph_type, depth, query, root, all_tenants):
        TopologyController._check_input_para(graph_type,
                                             depth,
                                             query,
                                             root,
                                             all_tenants)

        try:
            graph_data = pecan.request.client.call(pecan.request.context,
                                                   'get_topology',
                                                   graph_type=graph_type,
                                                   depth=depth,
                                                   query=query,
                                                   root=root,
                                                   all_tenants=all_tenants)
            graph = decompress_obj(graph_data)
            if graph_type == 'graph':
                return graph
            if graph_type == 'tree':
                if nx.__version__ >= '2.0':
                    node_id = ''
                    for node in graph['nodes']:
                        if (root and node[VProps.VITRAGE_ID] == root) or \
                                (not root and node[VProps.ID] == CLUSTER_ID):
                            node_id = node[VProps.GRAPH_INDEX]
                            break
                else:
                    node_id = CLUSTER_ID
                    if root:
                        for node in graph['nodes']:
                            if node[VProps.VITRAGE_ID] == root:
                                node_id = node[VProps.ID]
                                break
                return TopologyController.as_tree(graph, node_id)

        except Exception:
            LOG.exception('failed to get topology.')
            abort(404, 'Failed to get topology.')

    @staticmethod
    def as_tree(graph, root=OPENSTACK_CLUSTER, reverse=False):
        if nx.__version__ >= '2.0':
            linked_graph = json_graph.node_link_graph(
                graph, attrs={'name': 'graph_index'})
        else:
            linked_graph = json_graph.node_link_graph(graph)
        if 0 == nx.number_of_nodes(linked_graph):
            return {}
        if reverse:
            linked_graph = linked_graph.reverse()
        if nx.__version__ >= '2.0':
            return json_graph.tree_data(
                linked_graph,
                root=root,
                attrs={'id': 'graph_index', 'children': 'children'})
        else:
            return json_graph.tree_data(linked_graph, root=root)

    @staticmethod
    def _check_input_para(graph_type, depth, query, root, all_tenants):
        if graph_type == 'graph' and depth is not None and root is None:
            LOG.exception("Graph-type 'graph' requires a 'root' with 'depth'")
            abort(403, "Graph-type 'graph' requires a 'root' with 'depth'")
