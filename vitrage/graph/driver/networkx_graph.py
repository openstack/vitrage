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

from collections import defaultdict
import copy
import json
import networkx as nx
from networkx.algorithms.operators.binary import compose
from networkx.readwrite import json_graph
import pickle

from oslo_log import log as logging

from vitrage.common.constants import VertexProperties as VProps
from vitrage.graph.algo_driver.networkx_algorithm import NXAlgorithm
from vitrage.graph.driver.elements import Edge
from vitrage.graph.driver.elements import Vertex
from vitrage.graph.driver.graph import Direction
from vitrage.graph.driver.graph import Graph
from vitrage.graph.driver.notifier import Notifier
from vitrage.graph.filter import check_filter
from vitrage.graph.query import create_predicate

LOG = logging.getLogger(__name__)


def edge_copy(source_id, target_id, label, data):
    return Edge(source_id=source_id, target_id=target_id,
                label=label, properties=copy.copy(data))


def vertex_copy(v_id, data):
    return Vertex(vertex_id=v_id, properties=copy.copy(data))


class NXGraph(Graph):

    GRAPH_TYPE = "networkx"

    def __init__(self,
                 name='networkx_graph',
                 vertices=None,
                 edges=None):
        super(NXGraph, self).__init__(name, NXGraph.GRAPH_TYPE)
        self._g = nx.MultiDiGraph()
        self.add_vertices(vertices)
        self.add_edges(edges)
        self.ready = False

    def __len__(self):
        return len(self._g)

    @property
    def algo(self):
        return NXAlgorithm(self)

    def copy(self):
        # Networkx graph copy is very slow, so we implement
        nodes = self._g.nodes(data=True)
        vertices = [Vertex(vertex_id=n, properties=data) for n, data in nodes]
        edges_iter = self._g.edges(data=True, keys=True)
        edges = [Edge(source_id=u, target_id=v, label=l, properties=data)
                 for u, v, l, data in edges_iter]
        return NXGraph(self.name, vertices, edges)

    @Notifier.update_notify
    def add_vertex(self, v):
        """Add a vertex to the graph

        :type v: Vertex
        """
        # Call a private method, so to separate the notifier from logic
        self._add_vertex(v)

    def _add_vertex(self, v):
        properties_copy = copy.copy(v.properties)
        if properties_copy:
            self._g.add_node(v.vertex_id, **properties_copy)
        else:
            self._g.add_node(v.vertex_id)

    @Notifier.update_notify
    def add_edge(self, e):
        """Add an edge to the graph

        :type e: Edge
        """
        # Call a private method, so to separate the notifier from logic
        self._add_edge(e)

    def _add_edge(self, e):
        properties_copy = copy.copy(e.properties)
        if properties_copy:
            self._g.add_edge(e.source_id, e.target_id,
                             e.label, **properties_copy)
        else:
            self._g.add_edge(e.source_id, e.target_id, e.label)

    def get_vertex(self, v_id):
        """Fetch a vertex from the graph

        :rtype: Vertex
        """
        properties = self._g.nodes.get(v_id, None)
        if properties is not None:
            return vertex_copy(v_id, properties)
        LOG.debug("get_vertex item not found. v_id=%s", v_id)
        return None

    def get_edge(self, source_id, target_id, label):
        try:
            properties = self._g.adj[source_id][target_id][label]
        except KeyError:
            LOG.debug("get_edge item not found. source_id=%s, target_id=%s, "
                      "label=%s", source_id, target_id, label)
            return None
        if properties is not None:
            return edge_copy(source_id, target_id, label, properties)
        return None

    def get_edges(self,
                  v1_id,
                  v2_id=None,
                  direction=Direction.BOTH,
                  attr_filter=None):
        """Fetch multiple edges from the graph

        :rtype: set of Edge
        """
        def check_edge(edge_data):
            return check_filter(edge_data, attr_filter)

        nodes, edges = self._neighboring_nodes_edges_query(
            v1_id, edge_predicate=check_edge, direction=direction)

        edge_copies = set(edge_copy(u, v, label, data)
                          for u, v, label, data in edges)

        if v2_id:
            edge_copies = [e for e in edge_copies if e.has_vertex(v2_id)]

        return edge_copies

    def _get_edges_by_direction(self, v_id, direction):
        """Get all the edges from the vertex according to the direction

        :return: all the neighboring edges that match the filter
        :rtype: list of tuples (source_id, target_id, label, data)
        """
        if direction == Direction.BOTH:
            edges = []
            edges.extend(self._get_edges_by_direction(v_id, Direction.IN))
            edges.extend(self._get_edges_by_direction(v_id, Direction.OUT))
            return edges
        if direction == Direction.OUT:
            return self._g.out_edges(nbunch=v_id, data=True, keys=True)
        else:  # IN
            return self._g.in_edges(nbunch=v_id, data=True, keys=True)

    def num_vertices(self):
        return len(self._g)

    def num_edges(self):
        return self._g.number_of_edges()

    @Notifier.update_notify
    def update_vertex(self, v, overwrite=True):
        """Update the vertex properties

        :param v: the vertex with the new data
        :type v: Vertex

        :param overwrite: whether to overwrite existing properties
        :type overwrite: Boolean
        """
        orig_prop = self._g.nodes.get(v.vertex_id, None)
        if not orig_prop:
            self._add_vertex(v)
            return

        merged_props = \
            self._merged_properties(orig_prop, v.properties, overwrite)
        self._g.nodes[v.vertex_id].update(merged_props)

        for prop, value in v.properties.items():
            if value is None:
                del self._g.nodes[v.vertex_id][prop]

    @Notifier.update_notify
    def update_edge(self, e):
        """Update the edge properties

        :type e: Edge
        """
        orig_prop = self._g.adj.get(
            e.source_id, {}).get(
            e.target_id, {}).get(
            e.label, None)
        if not orig_prop:
            self._add_edge(e)
            return
        self._g.adj[e.source_id][e.target_id][e.label].update(e.properties)
        for prop, value in e.properties.items():
            if value is None:
                del self._g.adj[e.source_id][e.target_id][e.label][prop]

    @Notifier.update_notify
    def remove_vertex(self, v):
        """Remove Vertex v and its edges from the graph

        :type v: Vertex
        """

        self._g.remove_node(n=v.vertex_id)

    @Notifier.update_notify
    def remove_edge(self, e):
        """Remove an edge from the graph

        :type e: Edge
        """
        self._g.remove_edge(u=e.source_id, v=e.target_id, key=e.label)

    def get_vertices(self,
                     vertex_attr_filter=None,  # Dictionary of key value
                     query_dict=None):
        def check_vertex(vertex_data):
            return check_filter(vertex_data[1], vertex_attr_filter)

        if not query_dict:
            items = filter(check_vertex, self._g.nodes(data=True))
            return [vertex_copy(node, node_data) for node, node_data in items]
        elif not vertex_attr_filter:
            vertices = []
            match_func = create_predicate(query_dict)
            for node, node_data in self._g.nodes(data=True):
                v = vertex_copy(node, node_data)
                if match_func(v):
                    vertices.append(v)
            return vertices
        else:
            return []

    def get_vertices_ids(self, query_dict):
        if not query_dict:
            return list(self._g.nodes())

        vertices_ids = set()
        match_func = create_predicate(query_dict)
        for node, node_data in self._g.nodes(data=True):
            if match_func(node_data):
                vertices_ids.add(node)
        return vertices_ids

    def get_vertices_count(self, query_dict, group_by):
        vertices_counts = defaultdict(int)
        match_func = create_predicate(query_dict) if query_dict else None
        for node, node_data in self._g.nodes(data=True):
            if match_func is None or match_func(node_data):
                vertices_counts[node_data.get(group_by, '')] += 1
        return vertices_counts

    def get_vertices_by_key(self, key_values_hash):

        if key_values_hash in self.key_to_vertex_ids:
            vertices = []
            for vertex_id in self.key_to_vertex_ids[key_values_hash]:
                vertices.append(self.get_vertex(vertex_id))
            return vertices
        return []

    def neighbors(self, v_id, vertex_attr_filter=None, edge_attr_filter=None,
                  direction=Direction.BOTH):

        def check_edge(edge_data):
            return check_filter(edge_data, edge_attr_filter)

        def check_vertex(vertex_data):
            return check_filter(vertex_data, vertex_attr_filter)

        nodes, edges = self._neighboring_nodes_edges_query(
            v_id=v_id, vertex_predicate=check_vertex,
            edge_predicate=check_edge, direction=direction)
        vertices = [vertex_copy(n, data) for n, data in nodes]
        return vertices

    def _neighboring_nodes_edges_query(self, v_id,
                                       vertex_predicate=None,
                                       edge_predicate=None,
                                       direction=Direction.BOTH):
        if not direction:
            LOG.error("_neighboring_nodes_edges: direction cannot be None")
            raise AttributeError("neighbors: direction cannot be None")

        if not v_id:
            LOG.error("_neighboring_nodes_edges: v_id cannot be None")
            raise AttributeError("neighbors: v_id cannot be None")

        edges = self._get_edges_by_direction(v_id, direction)
        edges_filtered1 = []
        for edge in edges:
            if not edge_predicate or edge_predicate(edge[3]):
                edges_filtered1.append(edge)

        edges_filtered2 = []
        nodes = []

        for source_id, target_id, label, data in edges_filtered1:
            node_id_to_test = source_id if target_id == v_id else target_id
            node_data = self._g.nodes[node_id_to_test]
            if not vertex_predicate or vertex_predicate(node_data):
                edges_filtered2.append((source_id, target_id, label, data))
                nodes.append((node_id_to_test, node_data))
        return nodes, edges_filtered2

    def json_output_graph(self, **kwargs):
        """supports both 1.10<=networkx<2.0 and networx>=2.0 by returning the

        same json output regardless networx version

        :return: graph in json format
        """

        # TODO(annarez): when we decide to support networkx 2.0 with
        # versioning of Vitrage, we can move part of the logic to vitrageclient
        node_link_data = json_graph.node_link_data(self._g)
        node_link_data.update(kwargs)

        vitrage_id_to_index = dict()

        for index, node in enumerate(node_link_data['nodes']):
            vitrage_id_to_index[node[VProps.VITRAGE_ID]] = index
            if VProps.ID in self._g.nodes[node[VProps.ID]]:
                node[VProps.ID] = self._g.nodes[node[VProps.ID]][VProps.ID]
                node[VProps.GRAPH_INDEX] = index

        vers = nx.__version__
        if vers >= '2.0':
            for i in range(len(node_link_data['links'])):
                node_link_data['links'][i]['source'] = vitrage_id_to_index[
                    node_link_data['links'][i]['source']]
                node_link_data['links'][i]['target'] = vitrage_id_to_index[
                    node_link_data['links'][i]['target']]

        if kwargs.get('raw', False):
            return node_link_data
        else:
            return json.dumps(node_link_data)

    def write_gpickle(self):
        return pickle.dumps(self._g, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def read_gpickle(data, graph_to_update=None):
        if graph_to_update is not None:
            graph = graph_to_update
        else:
            graph = NXGraph()
        graph._g = pickle.loads(data)
        return graph

    def union(self, other_graph):
        """Union two graphs - add all vertices and edges of other graph

        :type other_graph: NXGraph
        """
        self._g = compose(self._g, other_graph._g)
