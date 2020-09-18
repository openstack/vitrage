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

"""Defines interface for Graph access and manipulation

Functions in this module are imported into the vitrage.graph namespace.
Call these functions from vitrage.graph namespace and not the
vitrage.graph.driver namespace.

"""
import abc
import copy

from vitrage.graph.driver.elements import Edge
from vitrage.graph.driver.elements import Vertex
from vitrage.graph.driver.notifier import Notifier


class Direction(object):
    OUT = 1
    IN = 2
    BOTH = 3


class Graph(object, metaclass=abc.ABCMeta):
    def __init__(self, name, graph_type, vertices=None, edges=None):
        """Create a Graph instance

        :type name: str
        :type graph_type: str
        :type vertices: list of Vertex
        :type edges: list of Edge
        :rtype: Graph
        """
        self.name = name
        self.graph_type = graph_type
        self.notifier = Notifier()

    def subscribe(self, function, finalization=False):
        """Subscribe to graph changes

        :param function: function will be called after each graph change
        :param finalization: function will be called after all non finalization

        Usage Example:
        graph = NXGraph()
        graph.subscribe(foo1, finalization=True)
        graph.subscribe(foo2, finalization=False)
        graph.subscribe(foo3, finalization=False)

        The order of the calls in this example wii be:
        1. foo2
        2. foo3
        3. foo1
        foo1 is called last because it subscribed as a finalization function
        """
        self.notifier.subscribe(function, finalization)

    def is_subscribed(self):
        return self.notifier.is_subscribed()

    def get_item(self, item):
        if isinstance(item, Edge):
            return self.get_edge(item.source_id, item.target_id, item.label)
        if isinstance(item, Vertex):
            return self.get_vertex(item.vertex_id)

    @property
    def algo(self):
        """Get graph algorithms

        :rtype: GraphAlgorithm
        """
        return None

    @abc.abstractmethod
    def copy(self):
        """Create a copy of the graph

        :return: A copy of the graph
        :rtype: Graph
        """
        pass

    @abc.abstractmethod
    def num_vertices(self):
        """Number of vertices in the graph

        :return:
        :rtype: int
        """
        pass

    @abc.abstractmethod
    def num_edges(self):
        """Number of edges in the graph

        :return:
        :rtype: int
        """
        pass

    @abc.abstractmethod
    def add_vertex(self, v):
        """Add a vertex to the graph

        A copy of Vertex v will be added to the graph.

        Example:
        --------
        graph = Graph()
        v = Vertex(vertex_id=1, properties={prop_key:prop_value})
        graph.add_vertex(v)

        :param v: the vertex to add
        :type v: Vertex
        """
        pass

    def add_vertices(self, vertices):
        """Add a list of vertices to the graph

        Uses add_vertex to add each vertex

        :param vertices:
        :type vertices:list of Vertex
        """
        if not vertices:
            return

        for v in vertices:
            self.add_vertex(v)

    @abc.abstractmethod
    def add_edge(self, e):
        """Add an edge to the graph

        A copy of Edge e will be added to the graph.

        Example:
        --------
        graph = Graph()

        v1_prop = {'prop_key':'some value for my first vertex'}
        v2_prop = {'prop_key':'another value for my second vertex'}
        v1 = Vertex(vertex_id=1, properties=v1_prop)
        v2 = Vertex(vertex_id=2, properties=v2_prop)
        graph.add_vertex(v1)
        graph.add_vertex(v2)

        e_prop = {'edge_prop':'and here is my edge property value'}
        e = Edge(source_id=v1.vertex_id, target_id=v2.vertex_id,
                 label='BELONGS', properties=e_prop)
        graph.add_edge(e)

        :param e: the edge to add
        :type e: Edge
        """
        pass

    def add_edges(self, edges):
        """Add a list of edges to the graph

        Uses add_edge to add each edge

        :param edges:
        :type edges:list of Edge
        """
        if not edges:
            return

        for e in edges:
            self.add_edge(e)

    @abc.abstractmethod
    def get_vertex(self, v_id):
        """Fetch a vertex from the graph

        :param v_id: vertex id
        :type v_id: str

        :return: the vertex or None if it does not exist
        :rtype: Vertex
        """
        pass

    @abc.abstractmethod
    def get_edge(self, source_id, target_id, label):
        """Fetch an edge from the graph,

        Fetch an edge from the graph, according to its two vertices and label

        :param source_id: vertex id of the source vertex
        :type source_id: str or None

        :param target_id: vertex id of the target vertex
        :type target_id: str

        :param label: the label property of the edge
        :type label: str or None

        :return: The edge between the two vertices or None
        :rtype: Edge
        """
        pass

    @abc.abstractmethod
    def get_edges(self,
                  v1_id,
                  v2_id=None,
                  direction=Direction.BOTH,
                  attr_filter=None):
        """Fetch multiple edges from the graph,

        Fetch all edges from the graph, according to its two vertices.
        If only one vertex id is given it finds all the edges from this vertex
        to all other vertices.
        If two vertices ids are given it finds all the edges between those two
        vertices.

        EXAMPLE
        -------
        v2_edges1 = g.get_edges(
            v_id=v2.vertex_id,
            attr_filter={'LABEL': 'ON'})

        v2_edges2 = g.get_edges(
            v_id=v2.vertex_id,
            attr_filter={'LABEL': ['ON', 'WITH']})

        :param v1_id: first vertex id of vertex
        :type v1_id: str

        :param v2_id: second vertex id of vertex
        :type v2_id: str

        :param direction: specify In/Out/Both for edge direction
        :type direction: int

        :param attr_filter: expected keys and values
        :type attr_filter: dict

        :return: All edges matching the requirements
        :rtype: set of Edge
        """
        pass

    @abc.abstractmethod
    def update_vertex(self, v, overwrite=True):
        """Update the vertex properties

        Update an existing vertex and create it if non existing.

        :param v: the vertex with the new data
        :type v: Vertex

        :param overwrite: whether to overwrite existing properties
        :type overwrite: Boolean
        """
        pass

    def update_vertices(self, vertices):
        """For each vertex, update its properties

        For each existing vertex, update its properties and create it if
        non existing.

        :param vertices: the vertex with the new data
        :type vertices: List
        """
        for v in vertices:
            self.update_vertex(v)

    @abc.abstractmethod
    def update_edge(self, e):
        """Update the edge properties

        Update an existing edge and create it if non existing.

        :param e: the edge with the new data
        :type e: Edge
        """
        pass

    @staticmethod
    def _merged_properties(base_props, updated_props, overwrite):
        if base_props is None:
            return copy.copy(updated_props)
        else:
            # Return all updated properties if overwrite is true, or only the
            # new properties otherwise
            return {k: v for k, v in updated_props.items()
                    if overwrite or k not in base_props}

    @abc.abstractmethod
    def remove_vertex(self, v):
        """Remove Vertex v and its edges from the graph

        :type v: Vertex
        """
        pass

    @abc.abstractmethod
    def remove_edge(self, e):
        """Remove an edge from the graph

        :type e: Edge
        """
        pass

    @abc.abstractmethod
    def get_vertices(self,
                     vertex_attr_filter=None,
                     query_dict=None):
        """Get vertices list with an optional match filter

        To filter the vertices, specify property values for
        the vertices

        Example:
        --------
        graph = Graph()

        v1_prop = {'prop_key':'some value for my first vertex'}
        v2_prop = {'prop_key':'another value for my second vertex'}
        v3_prop = {'prop_key':'YES'}
        v1 = Vertex(vertex_id=1, properties=v1_prop)
        v2 = Vertex(vertex_id=2, properties=v2_prop)
        v3 = Vertex(vertex_id=3, properties=v3_prop)
        graph.add_vertex(v1)
        graph.add_vertex(v2)
        graph.add_vertex(v3)

        all_vertices = graph.get_vertices()
        for v in all_vertices:
            do something with v
        filtered_vertices_list = graph.get_vertices(
                                    vertex_attr_filter={'prop_key':['YES']})

        :param vertex_attr_filter: expected keys and values
        :type vertex_attr_filter dict
        :param query_dict: expected query
        :type query_dict dict
        :return: A list of vertices that match the requested query
        :rtype: list of Vertex
        """
        pass

    @abc.abstractmethod
    def get_vertices_by_key(self,
                            key_values_hash):
        """Get vertices list according to their hash key

        The hash key is derived from their properties :
        See processor_utils - get_defining_properties


        :param key_values_hash: hash key
        :type key_values_hash str
        """
        pass

    @abc.abstractmethod
    def neighbors(self, v_id, vertex_attr_filter=None,
                  edge_attr_filter=None, direction=Direction.BOTH):
        """Get vertices that are neighboring to v_id vertex

        To filter the neighboring vertices, specify property values for
        the vertices or for the edges connecting them.

        Example:
        --------
        graph = Graph()

        v1_prop = {'prop_key':'some value for my first vertex'}
        v2_prop = {'prop_key':'another value for my second vertex'}
        v3_prop = {'prop_key':'YES'}
        v1 = Vertex(vertex_id=1, properties=v1_prop)
        v2 = Vertex(vertex_id=2, properties=v2_prop)
        v3 = Vertex(vertex_id=3, properties=v3_prop)
        graph.add_vertex(v1)
        graph.add_vertex(v2)
        graph.add_vertex(v3)

        e_prop = {'edge_prop':'and here is my edge property value'}
        e1 = Edge(source_id=v1.vertex_id, target_id=v2.vertex_id,
                 label='BELONGS', properties=e_prop)
        e2 = Edge(source_id=v1.vertex_id, target_id=v3.vertex_id,
                 label='ON', properties=e_prop)
        graph.add_edge(e1)
        graph.add_edge(e2)

        vertices_list1 = graph.neighbors(v_id=v1.vertex_id,
                               vertex_attr_filter={'prop_key':'YES'},
                               edge_attr_filter={'LABEL':'ON})
        vertices_list2 = graph.neighbors(v_id=v1.vertex_id,
                               vertex_attr_filter={'prop_key':['YES', 'CAT']},
                               edge_attr_filter={'LABEL':['ON', 'WITH']})

        :param direction:
        :param v_id: vertex id
        :type v_id: str
        :param vertex_attr_filter: expected keys and values
        :type vertex_attr_filter dict
        :param edge_attr_filter: expected keys and values
        :type edge_attr_filter: dict
        :return: A list of vertices that match the requested query
        :rtype: list of Vertex
        """
        pass

    @abc.abstractmethod
    def json_output_graph(self, **kwargs):
        pass

    @abc.abstractmethod
    def union(self, other_graph):
        pass
