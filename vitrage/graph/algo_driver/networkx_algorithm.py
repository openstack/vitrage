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
from networkx import is_frozen
from oslo_log import log as logging

from vitrage.common.constants import EdgeProperties as EProps
from vitrage.graph.algo_driver.algorithm import GraphAlgorithm
from vitrage.graph.algo_driver.algorithm import Mapping
from vitrage.graph.algo_driver.sub_graph_matching import NEG_CONDITION
from vitrage.graph.algo_driver.sub_graph_matching import subgraph_matching
from vitrage.graph.driver import Direction
from vitrage.graph.filter import check_filter
from vitrage.graph.query import create_predicate

LOG = logging.getLogger(__name__)


class NXAlgorithm(GraphAlgorithm):

    def __init__(self, graph):
        """Create a new GraphAlgorithm

        :param graph: graph instance
        :type graph: driver.Graph
        """
        super(NXAlgorithm, self).__init__(graph)

    @classmethod
    def _create_new_graph(cls, *args, **kwargs):
        from vitrage.graph.driver.networkx_graph import NXGraph
        return NXGraph(args, **kwargs)

    def graph_query_vertices(self,
                             root_id,
                             query_dict=None,
                             depth=None,
                             direction=Direction.BOTH,
                             edge_query_dict=None):
        graph = self._create_new_graph('graph')

        root_data = self.graph._g.nodes[root_id]

        match_func = create_predicate(query_dict) if query_dict else None
        edge_match_func = create_predicate(edge_query_dict) \
            if edge_query_dict else None

        if match_func and not match_func(root_data):
            LOG.info('graph_query_vertices: root %s does not match filter %s',
                     root_id, query_dict)
            return graph

        n_result = []
        visited_nodes = set()
        n_result.append((root_id, self.graph.get_vertex(root_id).properties))
        e_result = []
        nodes_q = [(root_id, 0)]
        while nodes_q:
            node_id, curr_depth = nodes_q.pop(0)
            if (node_id in visited_nodes) or (depth and curr_depth >= depth):
                continue
            visited_nodes.add(node_id)
            (n_list, e_list) = self.graph._neighboring_nodes_edges_query(
                node_id,
                direction=direction,
                vertex_predicate=match_func,
                edge_predicate=edge_match_func)
            n_result.extend(n_list)
            e_result.extend(e_list)
            nodes_q.extend([(v_id, curr_depth + 1) for v_id, data in n_list])

        graph = self._create_new_graph(graph.name)
        for v_id, data in n_result:
            graph._g.add_node(v_id, **data)
        for source_id, target_id, label, data in e_result:
            graph._g.add_edge(source_id, target_id, label, **data)

        return graph

    def sub_graph_matching(self,
                           subgraph,
                           known_match,
                           validate=False):
        """Finds all the matching subgraphs in the graph

        In case the known_match has a subgraph edge with property
        "negative_condition" then run subgraph matching on the edge vertices
        and unite the results.
        Otherwise just run subgraph matching and return its result.

        :param subgraph: the subgraph to match
        :param known_match: starting point at the subgraph and the graph
        :param validate:
        :return: all the matching subgraphs in the graph
        """
        sge = known_match.subgraph_element
        ge = known_match.graph_element

        if not known_match.is_vertex and sge.get(NEG_CONDITION):
            source_matches = self._filtered_subgraph_matching(ge.source_id,
                                                              sge.source_id,
                                                              subgraph,
                                                              validate)
            target_matches = self._filtered_subgraph_matching(ge.target_id,
                                                              sge.target_id,
                                                              subgraph,
                                                              validate)

            return self._list_union(source_matches, target_matches)
        else:
            return subgraph_matching(self.graph,
                                     subgraph,
                                     [known_match],
                                     validate)

    def create_graph_from_matching_vertices(self,
                                            query_dict=None,
                                            edge_attr_filter=None):
        vertices_ids = self.graph.get_vertices_ids(query_dict=query_dict)
        graph = self._create_new_graph('graph')
        graph._g = self.graph._g.subgraph(vertices_ids)

        # delete non matching edges
        if edge_attr_filter:
            self.apply_edge_attr_filter(graph, edge_attr_filter)

        return graph

    def subgraph(self, entities):
        subgraph = self._create_new_graph('graph')
        subgraph._g = self.graph._g.subgraph(entities)
        return subgraph

    def _filtered_subgraph_matching(self,
                                    ge_v_id,
                                    sge_v_id,
                                    subgraph,
                                    validate):
        """Runs subgraph_matching on edges vertices with filtering

        Runs subgraph_matching on edges vertices after checking if that vertex
        has real neighbors in the entity graph.
        """
        if self.graph.neighbors(ge_v_id,
                                edge_attr_filter={EProps.VITRAGE_IS_DELETED:
                                                  False}):
            template_vertex = subgraph.get_vertex(sge_v_id)
            graph_vertex = self.graph.get_vertex(ge_v_id)
            match = Mapping(template_vertex, graph_vertex, True)
            return subgraph_matching(self.graph, subgraph, [match], validate)

        return []

    @staticmethod
    def _list_union(list_1, list_2):
        """Union of list that aren't hashable

        Can't use here set union because the items in the lists are
        dictionaries and they are not hashable for set.

        :return: list - union list
        """

        for target_item in list_2:
            if target_item not in list_1:
                list_1.append(target_item)

        return list_1

    @staticmethod
    def apply_edge_attr_filter(graph, edge_attr_filter):
        edges = graph._g.edges(data=True, keys=True)
        edges_to_remove = [(u, v, k) for (u, v, k, d) in edges
                           if not check_filter(d, edge_attr_filter)]

        if edges_to_remove and is_frozen(graph._g):
            graph._g = graph._g.copy()

        for source, target, key in edges_to_remove:
            graph._g.remove_edge(u=source, v=target, key=key)
