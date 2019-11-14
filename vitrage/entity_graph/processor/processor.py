# Copyright 2015 - Alcatel-Lucent
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
from oslo_log import log

from vitrage.common.constants import EntityCategory as ECategory
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.entity_graph.mappings.datasource_info_mapper import \
    DatasourceInfoMapper
from vitrage.entity_graph.processor import base as processor
from vitrage.entity_graph.processor import processor_utils as PUtils
from vitrage.entity_graph.processor.transformer_manager import \
    TransformerManager
from vitrage.graph import Direction

LOG = log.getLogger(__name__)


class Processor(processor.ProcessorBase):

    def __init__(self, e_graph=None):
        super(Processor, self).__init__()
        self.transformer_manager = TransformerManager()
        self.info_mapper = DatasourceInfoMapper()
        self._initialize_events_actions()
        self.entity_graph = e_graph

    def process_event(self, event):
        """Decides which action to run on given event

        Transforms the event into a tuple (vertex, neighbors,action).
        After transforming, it runs the correct action according to the
        action received from the transformer.

        :param event: The event to be processed
        :type event: Dictionary
        """

        LOG.debug('processor event:\n%s', event)

        self._enrich_event(event)
        entity = self.transformer_manager.transform(event)

        if entity.action not in self.actions:
            LOG.warning('Deprecated or unknown entity %s ignored', entity)
            return

        self._calculate_vitrage_aggregated_values(entity.vertex, entity.action)
        self._set_datasource_name(entity, event)
        self.actions[entity.action](entity.vertex, entity.neighbors)

    def create_entity(self, new_vertex, neighbors):
        """Adds new vertex to the entity graph

        Adds the entity to the entity graph, and connects it's neighbors

        :param new_vertex: The new vertex to add to graph
        :type new_vertex: Vertex

        :param neighbors: The neighbors of the new vertex
        :type neighbors: List
        """

        LOG.debug('Add entity to entity graph:\n%s', new_vertex)
        self._add_resource_details_to_alarm(new_vertex, neighbors)
        self.entity_graph.add_vertex(new_vertex)
        self._connect_neighbors(neighbors, set(), GraphAction.CREATE_ENTITY)

    def update_entity(self, updated_vertex, neighbors):
        """Updates the vertex in the entity graph

        Updates the in entity in the entity graph. In addition it removes old
        neighbor connections, and connects the new neighbors.

        :param updated_vertex: The vertex to be updated in the graph
        :type updated_vertex: Vertex

        :param neighbors: The neighbors of the updated vertex
        :type neighbors: List
        """

        LOG.debug('Update entity in entity graph:\n%s', updated_vertex)

        graph_vertex = self.entity_graph.get_vertex(updated_vertex.vertex_id)
        if graph_vertex and not PUtils.is_newer_vertex(graph_vertex,
                                                       updated_vertex):
            LOG.warning("Update event arrived later than expected - "
                        "graph_vertex: %s --- updated_vertex: %s",
                        graph_vertex, updated_vertex)
            return
        self._add_resource_details_to_alarm(updated_vertex, neighbors)
        PUtils.update_entity_graph_vertex(self.entity_graph,
                                          graph_vertex,
                                          updated_vertex)
        self._update_neighbors(updated_vertex, neighbors)

    def delete_entity(self, deleted_vertex, neighbors):
        """Deletes the vertex from the entity graph

        Marks the corresponding vertex and its edges as deleted

        :param deleted_vertex: The vertex to be deleted from the graph
        :type deleted_vertex: Vertex

        :param neighbors: The neighbors of the deleted vertex
        :type neighbors: List
        """

        LOG.debug('Delete entity from entity graph:\n%s', deleted_vertex)

        graph_vertex = self.entity_graph.get_vertex(deleted_vertex.vertex_id)

        if not graph_vertex:
            LOG.warning('Delete - vertex not found %s', deleted_vertex)
            return
        elif PUtils.is_deleted(graph_vertex):
            LOG.warning('Delete - vertex already deleted - '
                        "graph_vertex: %s --- deleted_vertex: %s",
                        graph_vertex, deleted_vertex)
            return
        elif not PUtils.is_newer_vertex(graph_vertex, deleted_vertex):
            LOG.warning("Delete event arrived later than expected - "
                        "graph_vertex: %s --- deleted_vertex: %s",
                        graph_vertex, deleted_vertex)
            return

        neighbor_vertices = self.entity_graph.neighbors(
            deleted_vertex.vertex_id)
        neighbor_edges = self.entity_graph.get_edges(
            deleted_vertex.vertex_id)

        for edge in neighbor_edges:
            PUtils.mark_deleted(self.entity_graph, edge)

        for vertex in neighbor_vertices:
            PUtils.delete_placeholder_vertex(self.entity_graph, vertex)

        PUtils.mark_deleted(self.entity_graph, deleted_vertex)

    def update_relationship(self, entity_vertex, neighbors):
        LOG.debug('Update relationship in entity graph:\n%s', neighbors)

        if entity_vertex:
            self.entity_graph.update_vertex(entity_vertex)
        for neighbor in neighbors:
            self.entity_graph.update_edge(neighbor.edge)

    def delete_relationship(self, updated_vertex, neighbors):
        LOG.debug('Delete relationship from entity graph:\n%s', neighbors)

        if updated_vertex:
            self.entity_graph.update_vertex(updated_vertex)
        for neighbor in neighbors:
            graph_edge = self.entity_graph.get_edge(neighbor.edge.source_id,
                                                    neighbor.edge.target_id,
                                                    neighbor.edge.label)
            if graph_edge:
                PUtils.mark_deleted(self.entity_graph, graph_edge)

    def remove_deleted_entity(self, vertex, neighbors):
        """Removes the deleted vertex from the entity graph

        Removes vertex that it's vitrage_is_deleted value is True

        :param vertex: The vertex to be removed from the graph
        :type vertex: Vertex

        :param neighbors: The neighbors of the deleted vertex
        :type neighbors: List - It's just a mock in this method
        """

        LOG.debug('Remove deleted entity from entity graph:\n%s', vertex)

        graph_vertex = self.entity_graph.get_vertex(vertex.vertex_id)

        if graph_vertex and PUtils.is_deleted(graph_vertex) and \
                PUtils.is_newer_vertex(graph_vertex, vertex):
            self.entity_graph.remove_vertex(vertex)
        else:
            LOG.warning("Remove deleted entity arrived on invalid resource: "
                        "deleted_vertex - %s, graph_vertex - %s",
                        vertex, graph_vertex)

    def _update_neighbors(self, vertex, neighbors):
        """Updates vertices neighbor connections

        1. Removes old neighbor connections
        2. connects the new neighbors.
        """

        (valid_edges, obsolete_edges) = self._find_edges_status(vertex,
                                                                neighbors)
        self._delete_old_connections(vertex, obsolete_edges)
        self._connect_neighbors(neighbors,
                                valid_edges,
                                GraphAction.UPDATE_ENTITY)

    def _connect_neighbors(self, neighbors, valid_edges, action):
        """Updates the neighbor vertex and adds the connection edges """
        if not neighbors:
            LOG.debug('connect_neighbors - nothing to do')
            return

        LOG.debug("Connect neighbors. Neighbors: %s, valid_edges: %s",
                  neighbors, valid_edges)
        for (vertex, edge) in neighbors:
            graph_vertex = self.entity_graph.get_vertex(vertex.vertex_id)
            if not graph_vertex or not PUtils.is_deleted(graph_vertex):
                if graph_vertex and not PUtils.is_newer_vertex(graph_vertex,
                                                               vertex):
                    LOG.warning("Neighbor update event arrived later than "
                                "expected - graph_vertex: %s --- "
                                "updated_vertex: %s", graph_vertex, vertex)
                else:
                    LOG.debug("Updates vertex: %s", vertex)
                    self._calculate_vitrage_aggregated_values(vertex, action)
                    PUtils.update_entity_graph_vertex(self.entity_graph,
                                                      graph_vertex,
                                                      vertex)
                if edge not in valid_edges:
                    LOG.debug("Updates edge: %s", edge)
                    self.entity_graph.update_edge(edge)
            else:
                LOG.debug("neighbor vertex wasn't updated: %s", vertex)

    def _delete_old_connections(self, vertex, obsolete_edges):
        """Deletes the "vertex" old connections

        Finds the old connections that are connected to updated_vertex,
        and marks them as deleted
        """
        if not obsolete_edges:
            LOG.debug('obsolete_edges - nothing to do')
            return

        LOG.debug('Delete old connections. Vertex:\n%s', vertex)
        # remove old edges and placeholder vertices if exist
        for edge in obsolete_edges:
            LOG.debug("Delete obsolete edge:\n%s", edge)
            PUtils.mark_deleted(self.entity_graph, edge)
            graph_ver = self.entity_graph.get_vertex(
                edge.other_vertex(vertex.vertex_id))
            PUtils.delete_placeholder_vertex(self.entity_graph, graph_ver)

    def _find_edges_status(self, vertex, neighbors):
        """Finds "vertex" valid and old connections

        Checks all the edges that are connected to the vertex in the entity
        graph, and finds which of them are old connections (edges that are no
        longer connected to those entities), and which are valid connections.
        """

        valid_edges = set()
        obsolete_edges = set()

        graph_neighbor_types = \
            PUtils.find_neighbor_types(neighbors)

        neighbor_edges = set(e for v, e in neighbors)
        for curr_edge in self.entity_graph.get_edges(vertex.vertex_id,
                                                     direction=Direction.BOTH):
            # check if the edge in the graph has a connection to the
            # same type of resources in the new neighbors list
            neighbor_vertex = self.entity_graph.get_vertex(
                curr_edge.other_vertex(vertex.vertex_id))

            is_connection_type_exist = PUtils.get_vertex_types(
                neighbor_vertex) in graph_neighbor_types

            if not is_connection_type_exist:
                valid_edges.add(curr_edge)
                continue

            if curr_edge in neighbor_edges:
                valid_edges.add(curr_edge)
            else:
                obsolete_edges.add(curr_edge)

        return valid_edges, obsolete_edges

    def _initialize_events_actions(self):
        self.actions = {
            GraphAction.CREATE_ENTITY: self.create_entity,
            GraphAction.UPDATE_ENTITY: self.update_entity,
            GraphAction.DELETE_ENTITY: self.delete_entity,
            GraphAction.UPDATE_RELATIONSHIP: self.update_relationship,
            GraphAction.DELETE_RELATIONSHIP: self.delete_relationship,
            GraphAction.REMOVE_DELETED_ENTITY: self.remove_deleted_entity,
        }

    def _calculate_vitrage_aggregated_values(self, vertex, action):
        LOG.debug("calculate event state")

        try:
            if action in [GraphAction.UPDATE_ENTITY,
                          GraphAction.DELETE_ENTITY,
                          GraphAction.CREATE_ENTITY]:
                graph_vertex = self.entity_graph.get_vertex(
                    vertex.vertex_id)
            elif action in [GraphAction.REMOVE_DELETED_ENTITY,
                            GraphAction.UPDATE_RELATIONSHIP,
                            GraphAction.DELETE_RELATIONSHIP]:
                return None
            else:
                LOG.error('unrecognized action: %s for vertex: %s',
                          action, vertex)
                return None

            self.info_mapper.vitrage_aggregate_values(vertex, graph_vertex)
        except Exception:
            LOG.exception("Calculate aggregated state failed.")

    def _enrich_event(self, event):
        attr = self.transformer_manager.get_enrich_query(event)
        if attr is None:
            return
        result = self.entity_graph.get_vertices(attr)
        event[TransformerBase.QUERY_RESULT] = result

    def _add_resource_details_to_alarm(self, vertex, neighbors):

        if not neighbors:
            return

        resource = None
        alarms = []

        if vertex.get(VProps.VITRAGE_CATEGORY) == ECategory.ALARM:
            alarms = [vertex]
            for neighbor in neighbors:
                if neighbor.vertex.get(VProps.VITRAGE_CATEGORY) ==\
                        ECategory.RESOURCE:
                    resource = neighbor.vertex
        elif vertex.get(VProps.VITRAGE_CATEGORY) == ECategory.RESOURCE:
            resource = vertex
            for neighbor in neighbors:
                if neighbor.vertex.get(VProps.VITRAGE_CATEGORY) == \
                        ECategory.ALARM:
                    alarms.append(neighbor.vertex)

        for alarm in alarms:
            if not resource:
                continue

            project_id = resource.get(VProps.PROJECT_ID)
            if not project_id:
                n_vertex = self.entity_graph.get_vertex(resource.vertex_id)
                project_id = n_vertex.get(VProps.PROJECT_ID) \
                    if n_vertex else None
            self.add_resource_details(
                alarm,
                r_id=resource.vertex_id,
                r_type=resource.get(VProps.VITRAGE_TYPE),
                r_project_id=project_id)

    @staticmethod
    def add_resource_details(alarm, r_id, r_type, r_project_id):
        alarm[VProps.VITRAGE_RESOURCE_ID] = r_id
        alarm[VProps.VITRAGE_RESOURCE_TYPE] = r_type
        if r_project_id:
            alarm[VProps.VITRAGE_RESOURCE_PROJECT_ID] = r_project_id

    @staticmethod
    def _set_datasource_name(entity, event):
        if entity.vertex and \
                (entity.action == GraphAction.CREATE_ENTITY or
                 entity.action == GraphAction.UPDATE_ENTITY):
            datasource_name = event.get(VProps.VITRAGE_DATASOURCE_NAME)
            if datasource_name:
                entity.vertex.properties[VProps.VITRAGE_DATASOURCE_NAME] = \
                    datasource_name
