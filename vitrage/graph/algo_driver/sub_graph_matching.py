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

from oslo_log import log as logging

from vitrage.common.exception import VitrageAlgorithmError
from vitrage.graph.filter import check_filter

LOG = logging.getLogger(__name__)

MAPPED_V_ID = 'mapped_v_id'
NEIGHBORS_MAPPED = 'neighbors_mapped'
GRAPH_VERTEX = 'graph_vertex'
NEG_VERTEX = 'negative vertex'
NEG_CONDITION = 'negative_condition'


def subgraph_matching(base_graph, subgraph, matches, validate=False):
    """Find all occurrences of subgraph in the graph

    In the following, a partial mapping is a copy of the sub-graph.
    As we go, vertices of curr_mapping graph will be updated with new
    fields used only for the traversal:

     - MAPPED_V_ID:
       The vertex_id of the corresponding vertex in the graph.
       If it is not empty, than this vertex is already mapped

     - NEIGHBORS_MAPPED:
       True or None. When set True it means all the
       neighbors of this vertex have already been mapped

    Implementation Details:
    ----------------------

    - Init Step:
      copy the sub-graph to create the first candidate mapping graph. In which
      known vertices mappings are added to vertices MAPPED_V_ID. So, we now
      have a sub-graph copy where some of the vertices already have a mapping

    Main loop steps:

    - Steps 1:
      Pop a partially mapped sub-graph from the queue.
      If all its vertices have a MAPPED_V_ID, add it to final mappings

    - Steps 2 & 3:
      Find one template vertex that is not mapped but has a mapped neighbor

    - Step 4: CHECK PROPERTIES
      In the graph find candidate vertices that are linked to that neighbor
      and match the template vertex properties

    - Step 5: CHECK STRUCTURE
      Filter candidate vertices according to edges
    """
    final_subgraphs = []
    initial_sg = _create_initial_subgraph(matches,
                                          base_graph,
                                          subgraph,
                                          validate)
    if not initial_sg:
        LOG.warning('subgraph_matching:Initial sub-graph creation failed')
        LOG.warning('subgraph_matching: Known matches: %s', matches)
        return final_subgraphs
    queue = [initial_sg]

    while queue:
        curr_subgraph = queue.pop(0)

        # STEP 1: STOPPING CONDITION
        mapped_vertices = list(filter(
            lambda v: v.get(MAPPED_V_ID),
            curr_subgraph.get_vertices()))
        if len(mapped_vertices) == subgraph.num_vertices():
            final_subgraphs.append(curr_subgraph)
            continue

        # STEP 2: CAN WE THROW THIS SUB-GRAPH?
        vertices_with_unmapped_neighbors = list(filter(
            lambda v: not v.get(NEIGHBORS_MAPPED),
            mapped_vertices))
        if not vertices_with_unmapped_neighbors:
            continue

        # STEP 3: FIND A SUB-GRAPH VERTEX TO MAP
        v_with_unmapped_neighbors = _choose_vertex(
            vertices_with_unmapped_neighbors,
            curr_subgraph)

        unmapped_neighbors = list(filter(
            lambda v: not v.get(MAPPED_V_ID),
            curr_subgraph.neighbors(v_with_unmapped_neighbors.vertex_id)))
        if not unmapped_neighbors:
            # Mark vertex as NEIGHBORS_MAPPED=True
            v_with_unmapped_neighbors[NEIGHBORS_MAPPED] = True
            curr_subgraph.update_vertex(v_with_unmapped_neighbors)
            queue.append(curr_subgraph)
            continue
        subgraph_vertex_to_map = _choose_vertex(
            unmapped_neighbors,
            curr_subgraph,
            curr_v=v_with_unmapped_neighbors)

        # STEP 4: PROPERTIES CHECK
        graph_candidate_vertices = base_graph.neighbors(
            v_id=v_with_unmapped_neighbors[MAPPED_V_ID],
            vertex_attr_filter=subgraph_vertex_to_map)

        graph_candidate_vertices = \
            _remove_used_graph_candidates(graph_candidate_vertices,
                                          curr_subgraph)

        # STEP 5: STRUCTURE CHECK
        edges = _get_edges_to_mapped_vertices(curr_subgraph,
                                              subgraph_vertex_to_map.vertex_id)
        neg_edges = set(e for e in edges if e.get(NEG_CONDITION))
        pos_edges = edges.difference(neg_edges)

        if not graph_candidate_vertices and neg_edges and not pos_edges:
            subgraph_vertex_to_map[MAPPED_V_ID] = NEG_VERTEX
            curr_subgraph.update_vertex(subgraph_vertex_to_map)
            queue.append(curr_subgraph)
            continue

        found_subgraphs = []
        remaining_items = len(graph_candidate_vertices)
        for graph_vertex in graph_candidate_vertices:
            subgraph_vertex_to_map[MAPPED_V_ID] = graph_vertex.vertex_id
            subgraph_vertex_to_map[GRAPH_VERTEX] = graph_vertex
            curr_subgraph.update_vertex(subgraph_vertex_to_map)
            if not _graph_contains_subgraph_edges(base_graph,
                                                  curr_subgraph,
                                                  pos_edges):
                continue
            if not _graph_contains_subgraph_edges(base_graph,
                                                  curr_subgraph,
                                                  neg_edges):
                del found_subgraphs[:]
                break
            if neg_edges and not pos_edges:
                subgraph_vertex_to_map[MAPPED_V_ID] = NEG_VERTEX
                curr_subgraph.update_vertex(subgraph_vertex_to_map)

            remaining_items -= 1  # no need to copy the last one
            found_subgraphs.append(
                curr_subgraph.copy() if remaining_items else curr_subgraph)

        queue.extend(found_subgraphs)

    # Last thing: Convert results to the expected format!
    return _generate_result(final_subgraphs)


def _generate_result(final_subgraphs):
    result = []
    for mapping in final_subgraphs:
        subgraph_vertices = dict()
        for v in mapping.get_vertices():
            v_id = v[MAPPED_V_ID]
            if isinstance(v_id, str) and v_id is not NEG_VERTEX:
                subgraph_vertices[v.vertex_id] = v[GRAPH_VERTEX]

        if subgraph_vertices not in result:
            result.append(subgraph_vertices)
    return result


def _choose_vertex(vertices, subgraph, curr_v=None):
    """Return a vertex with a positive edge if exists, otherwise the first one.

    """
    for v in vertices:
        curr_vertex_id = curr_v.vertex_id if curr_v else None
        if not subgraph.get_edges(v.vertex_id, curr_vertex_id,
                                  attr_filter={NEG_CONDITION: True}):
            return v
    return vertices.pop(0)


def _get_edges_to_mapped_vertices(graph, vertex_id):
    """Get all edges (to/from) vertex where neighbor has a MAPPED_V_ID

    :type graph: driver.Graph
    :type vertex_id: str
    :rtype: set of driver.Edge
    """
    subgraph_edges_to_mapped_vertices = []
    for e in graph.get_edges(vertex_id):
        t_neighbor = graph.get_vertex(e.other_vertex(vertex_id))
        if not t_neighbor:
            raise VitrageAlgorithmError('Cant get vertex for edge %s' % e)
        if t_neighbor and t_neighbor.get(MAPPED_V_ID):
            subgraph_edges_to_mapped_vertices.append(e)
    return set(subgraph_edges_to_mapped_vertices)


def _graph_contains_subgraph_edges(graph, subgraph, subgraph_edges):
    """Check if graph contains all the expected edges

    For each (sub-graph) expected edge, check if a corresponding edge exists
    in the graph with relevant properties check

    :type graph: driver.Graph
    :type subgraph: driver.Graph
    :type subgraph_edges: set of driver.Edge
    :rtype: bool
    """
    for e in subgraph_edges:
        graph_v_id_source = subgraph.get_vertex(e.source_id).get(MAPPED_V_ID)
        graph_v_id_target = subgraph.get_vertex(e.target_id).get(MAPPED_V_ID)
        if not graph_v_id_source or not graph_v_id_target:
            raise VitrageAlgorithmError('Cant get vertex for edge %s' % e)
        found_graph_edge = graph.get_edge(graph_v_id_source,
                                          graph_v_id_target,
                                          e.label)

        if not found_graph_edge and e.get(NEG_CONDITION):
            continue

        if not found_graph_edge or not check_filter(found_graph_edge, e,
                                                    NEG_CONDITION):
            return False
    return True


def _create_initial_subgraph(known_matches, graph, subgraph, validate=False):
    """Create initial mapping graph from sub graph and known matches

    copy the sub-graph to create the first candidate mapping graph.
    In which known vertices mappings are added to vertices MAPPED_V_ID
    """
    mapping = subgraph.copy()
    for match in known_matches:
        if match.is_vertex:
            if not _update_mapping_for_vertex(match, mapping, graph, validate):
                return None
            subgraph_id = match.subgraph_element.vertex_id
            edges = _get_edges_to_mapped_vertices(mapping, subgraph_id)

        else:  # is edge
            if not _update_mapping_for_edge(match, mapping, graph, validate):
                return None
            edges = _get_related_edges(mapping, match, subgraph, validate)
        if not _graph_contains_subgraph_edges(graph, mapping, edges):
            return None
    return mapping


def _get_related_edges(mapping, match, subgraph, validate):
    sub_target_id = match.subgraph_element.target_id
    sub_source_id = match.subgraph_element.source_id
    edges = _get_edges_to_mapped_vertices(mapping, sub_source_id)
    edges.union(_get_edges_to_mapped_vertices(mapping, sub_target_id))
    if not validate:  # no need to check the mapped edge
        known_edge = subgraph.get_edge(
            sub_source_id,
            sub_target_id,
            match.subgraph_element.label
        )
        edges.remove(known_edge)
    return edges


def _update_mapping(subgraph, graph, subgraph_id, graph_id, validate):
    subgraph_vertex = subgraph.get_vertex(subgraph_id)
    graph_vertex = graph.get_vertex(graph_id)
    if validate:
        if not check_filter(graph_vertex, subgraph_vertex, MAPPED_V_ID):
            return False
    subgraph_vertex[MAPPED_V_ID] = graph_id
    subgraph_vertex[GRAPH_VERTEX] = graph_vertex
    subgraph.update_vertex(subgraph_vertex)
    return True


def _update_mapping_for_vertex(known_match, mapping, graph, validate):
    subgraph_id = known_match.subgraph_element.vertex_id
    graph_id = known_match.graph_element.vertex_id
    return _update_mapping(mapping, graph, subgraph_id, graph_id, validate)


def _update_mapping_for_edge(known_match, mapping, graph, validate):
    s_id = known_match.graph_element.source_id
    sub_s_id = known_match.subgraph_element.source_id
    if not _update_mapping(mapping, graph, sub_s_id, s_id, validate):
        return False

    t_id = known_match.graph_element.target_id
    sub_t_id = known_match.subgraph_element.target_id
    return _update_mapping(mapping, graph, sub_t_id, t_id, validate)


def _remove_used_graph_candidates(graph_candidate_vertices, curr_subgraph):
    ver_to_remove = []
    for candidate in graph_candidate_vertices:
        for sub_ver in curr_subgraph.get_vertices():
            if sub_ver.get(GRAPH_VERTEX, False) and \
                    sub_ver[GRAPH_VERTEX].vertex_id == candidate.vertex_id:
                ver_to_remove.append(candidate)
    return [v for v in graph_candidate_vertices if v not in ver_to_remove]
