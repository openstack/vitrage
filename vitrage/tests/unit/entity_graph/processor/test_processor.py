# Copyright 2015 - Alcatel-Lucent
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

from testtools import matchers

from vitrage.common.constants import DatasourceAction as DSAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeProperties as EProps
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.transformer_base import Neighbor
from vitrage.entity_graph.mappings.operational_resource_state import \
    OperationalResourceState
from vitrage.entity_graph.processor import processor_utils as PUtils
import vitrage.graph.utils as graph_utils
from vitrage.tests.unit.entity_graph.base import TestEntityGraphUnitBase
from vitrage.utils.datetime import utcnow


class TestProcessor(TestEntityGraphUnitBase):

    ZONE_SPEC = 'ZONE_SPEC'
    HOST_SPEC = 'HOST_SPEC'
    INSTANCE_SPEC = 'INSTANCE_SPEC'
    NUM_VERTICES_AFTER_CREATION = 2
    NUM_EDGES_AFTER_CREATION = 1
    NUM_VERTICES_AFTER_DELETION = 1
    NUM_EDGES_AFTER_DELETION = 0

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    def setUp(self):
        super(TestProcessor, self).setUp()
        self.load_datasources()

    def test_process_event(self):
        # check create instance event
        processor = self.create_processor_and_graph()
        event = self._create_event(spec_type=self.INSTANCE_SPEC,
                                   datasource_action=DSAction.INIT_SNAPSHOT)
        processor.process_event(event)
        self._check_graph(processor, self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION)

        # check update instance event (versioned notification format)
        event[DSProps.DATASOURCE_ACTION] = DSAction.UPDATE
        event[DSProps.EVENT_TYPE] = 'instance.volume_attach.end'

        nova_object_data = {
            'host_name': 'new_host',
            'uuid': event['id'],
            'state': event['status'],
            'host': event['OS-EXT-SRV-ATTR:host']
        }
        event['nova_object.data'] = nova_object_data

        processor.process_event(event)
        self._check_graph(processor, self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION)

        # check delete instance event
        event[DSProps.DATASOURCE_ACTION] = DSAction.UPDATE
        event[DSProps.EVENT_TYPE] = 'compute.instance.delete.end'
        processor.process_event(event)
        self._check_graph(processor, self.NUM_VERTICES_AFTER_DELETION,
                          self.NUM_EDGES_AFTER_DELETION)

    def test_create_entity_with_placeholder_neighbor(self):
        # create instance event with host neighbor and check validity
        self._create_and_check_entity()

    def test_update_entity_state(self):
        # create instance event with host neighbor and check validity
        (vertex, neighbors, processor) =\
            self._create_and_check_entity(status='STARTING')

        # check added entity
        vertex = processor.entity_graph.get_vertex(vertex.vertex_id)
        self.assertEqual('STARTING', vertex.properties[VProps.STATE])

        # update instance event with state running
        vertex.properties[VProps.STATE] = 'RUNNING'
        vertex.properties[VProps.VITRAGE_SAMPLE_TIMESTAMP] = str(utcnow())
        processor.update_entity(vertex, neighbors)

        # check state
        self._check_graph(processor, self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION)
        vertex = processor.entity_graph.get_vertex(vertex.vertex_id)
        self.assertEqual('RUNNING', vertex.properties[VProps.STATE])

    def test_change_parent(self):
        # create instance event with host neighbor and check validity
        (vertex, neighbors, processor) = self._create_and_check_entity()

        # update instance event with state running
        (neighbor_vertex, neighbor_edge) = neighbors[0]
        old_neighbor_id = neighbor_vertex.vertex_id
        neighbor_vertex.properties[VProps.ID] = 'newhost-2'
        neighbor_vertex.vertex_id = 'RESOURCE_HOST_newhost-2'
        neighbor_edge.source_id = 'RESOURCE_HOST_newhost-2'
        processor.update_entity(vertex, neighbors)

        # check state
        self._check_graph(processor, self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION)
        neighbor_vertex = \
            processor.entity_graph.get_vertex(old_neighbor_id)
        self.assertIsNone(neighbor_vertex)

    def test_delete_entity(self):
        # create instance event with host neighbor and check validity
        (vertex, neighbors, processor) = self._create_and_check_entity()

        # delete entity
        processor.delete_entity(vertex, neighbors)

        # check deleted entity
        self._check_graph(processor, self.NUM_VERTICES_AFTER_DELETION,
                          self.NUM_EDGES_AFTER_DELETION)
        self.assertTrue(PUtils.is_deleted(vertex))

    def test_update_relationship(self):
        # setup
        vertex1, neighbors1, processor = self._create_entity(
            spec_type=self.INSTANCE_SPEC,
            datasource_action=DSAction.INIT_SNAPSHOT)
        vertex2, neighbors2, processor = self._create_entity(
            spec_type=self.INSTANCE_SPEC,
            datasource_action=DSAction.INIT_SNAPSHOT,
            processor=processor)
        self.assertEqual(2, processor.entity_graph.num_edges())

        new_edge = graph_utils.create_edge(vertex1.vertex_id,
                                           vertex2.vertex_id,
                                           'backup')
        mock_neighbor = graph_utils.create_vertex(
            "asdjashdkahsdashdalksjhd",
            vitrage_category="RESOURCE",
            vitrage_type="nova.instance",
            entity_id="wtw64768476",
            entity_state="AVAILABLE",
        )
        new_neighbors = [Neighbor(mock_neighbor, new_edge)]

        # action
        processor.update_relationship(vertex1, new_neighbors)

        # test assertions
        self.assertEqual(3, processor.entity_graph.num_edges())

    def test_delete_relationship(self):
        # setup
        vertex1, neighbors1, processor = self._create_entity(
            spec_type=self.INSTANCE_SPEC,
            datasource_action=DSAction.INIT_SNAPSHOT)
        vertex2, neighbors2, processor = self._create_entity(
            spec_type=self.INSTANCE_SPEC,
            datasource_action=DSAction.INIT_SNAPSHOT,
            processor=processor)
        self.assertEqual(2, processor.entity_graph.num_edges())

        new_edge = graph_utils.create_edge(vertex1.vertex_id,
                                           vertex2.vertex_id,
                                           'backup')
        processor.entity_graph.add_edge(new_edge)
        self.assertEqual(3, processor.entity_graph.num_edges())
        new_neighbors = [Neighbor(vertex1, new_edge)]

        # action
        processor.delete_relationship(vertex2, new_neighbors)

        # test assertions
        edge_from_graph = processor.entity_graph.get_edge(vertex1.vertex_id,
                                                          vertex2.vertex_id,
                                                          'backup')
        self.assertEqual(3, processor.entity_graph.num_edges())
        self.assertTrue(edge_from_graph[EProps.VITRAGE_IS_DELETED])

    def test_remove_deleted_entity(self):
        # setup
        vertex, neighbors, processor = self._create_entity(
            spec_type=self.INSTANCE_SPEC,
            datasource_action=DSAction.INIT_SNAPSHOT)
        self.assertEqual(1, processor.entity_graph.num_edges())
        vertex[VProps.VITRAGE_IS_DELETED] = True
        processor.entity_graph.update_vertex(vertex)

        # action
        processor.remove_deleted_entity(vertex, None)

        # test assertions
        self.assertEqual(0, processor.entity_graph.num_edges())

    def test_update_neighbors(self):
        # create instance event with host neighbor and check validity
        (vertex, neighbors, processor) = self._create_and_check_entity()

        # update instance event with state running
        (neighbor_vertex, neighbor_edge) = neighbors[0]
        old_neighbor_id = neighbor_vertex.vertex_id
        neighbor_vertex.properties[VProps.ID] = 'newhost-2'
        neighbor_vertex.vertex_id = 'RESOURCE_HOST_newhost-2'
        neighbor_edge.source_id = 'RESOURCE_HOST_newhost-2'
        processor._update_neighbors(vertex, neighbors)

        # check state
        self._check_graph(processor, self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION)
        self.assertIsNone(processor.entity_graph.get_vertex(old_neighbor_id))

        # update instance with the same neighbor
        processor._update_neighbors(vertex, neighbors)

        # check state
        self._check_graph(processor, self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION)

    def test_update_neighbors_by_changing_label(self):
        # create instance event with host neighbor and check validity
        (vertex, neighbors, processor) = self._create_and_check_entity()

        # update instance event with state running
        (neighbor_vertex, neighbor_edge) = neighbors[0]
        old_label = neighbor_edge.label
        neighbor_vertex[VProps.VITRAGE_IS_PLACEHOLDER] = False
        processor.entity_graph.update_vertex(neighbor_vertex)
        neighbor_vertex[VProps.VITRAGE_IS_PLACEHOLDER] = True
        neighbor_edge.label = 'new label'

        processor._update_neighbors(vertex, neighbors)

        # check state
        self._check_graph(processor,
                          self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION,
                          vertex_id=vertex.vertex_id)
        old_edge = processor.entity_graph.get_edge(neighbor_vertex.vertex_id,
                                                   vertex.vertex_id,
                                                   old_label)
        new_edge = processor.entity_graph.get_edge(neighbor_vertex.vertex_id,
                                                   vertex.vertex_id,
                                                   neighbor_edge.label)
        self.assertIsNotNone(old_edge)
        self.assertTrue(old_edge[EProps.VITRAGE_IS_DELETED])
        self.assertIsNotNone(new_edge)
        self.assertFalse(new_edge[EProps.VITRAGE_IS_DELETED])

        # update instance with the same neighbor
        processor._update_neighbors(vertex, neighbors)

        # check state
        self._check_graph(processor,
                          self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION,
                          vertex_id=vertex.vertex_id)

    def test_update_neighbors_by_changing_label_with_placeholder(self):
        # create instance event with host neighbor and check validity
        (vertex, neighbors, processor) = self._create_and_check_entity()

        # update instance event with state running
        (neighbor_vertex, neighbor_edge) = neighbors[0]
        old_label = neighbor_edge.label
        neighbor_edge.label = 'new label'

        processor._update_neighbors(vertex, neighbors)

        # check state
        self._check_graph(processor,
                          self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION,
                          vertex_id=vertex.vertex_id)
        old_edge = processor.entity_graph.get_edge(neighbor_vertex.vertex_id,
                                                   vertex.vertex_id,
                                                   old_label)
        new_edge = processor.entity_graph.get_edge(neighbor_vertex.vertex_id,
                                                   vertex.vertex_id,
                                                   neighbor_edge.label)
        self.assertIsNone(old_edge)
        self.assertIsNotNone(new_edge)
        self.assertFalse(new_edge[EProps.VITRAGE_IS_DELETED])

        # update instance with the same neighbor
        processor._update_neighbors(vertex, neighbors)

        # check state
        self._check_graph(processor,
                          self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION,
                          vertex_id=vertex.vertex_id)

    def test_delete_old_connections(self):
        # create instance event with host neighbor and check validity
        (vertex, neighbors, processor) = self._create_and_check_entity()

        # delete entity
        processor._delete_old_connections(vertex, [neighbors[0][1]])

        # check deleted entity
        self._check_graph(processor,
                          self.NUM_VERTICES_AFTER_DELETION,
                          self.NUM_EDGES_AFTER_DELETION)

    def test_calculate_vitrage_aggregated_state(self):
        # setup
        instances = []
        for i in range(6):
            (vertex, neighbors, processor) = self._create_and_check_entity()
            instances.append((vertex, processor))

        # action
        # state already exists and its updated
        instances[0][0][VProps.STATE] = 'SUSPENDED'
        instances[0][1]._calculate_vitrage_aggregated_values(
            instances[0][0], GraphAction.UPDATE_ENTITY)

        # vitrage state doesn't exist and its updated
        instances[1][0][VProps.STATE] = None
        instances[1][1].entity_graph.update_vertex(instances[1][0])
        instances[1][0][VProps.VITRAGE_STATE] = \
            OperationalResourceState.SUBOPTIMAL
        instances[1][1]._calculate_vitrage_aggregated_values(
            instances[1][0], GraphAction.UPDATE_ENTITY)

        # state exists and vitrage state changes
        instances[2][0][VProps.VITRAGE_STATE] = \
            OperationalResourceState.SUBOPTIMAL
        instances[2][1]._calculate_vitrage_aggregated_values(
            instances[2][0], GraphAction.UPDATE_ENTITY)

        # vitrage state exists and state changes
        instances[3][0][VProps.STATE] = None
        instances[3][0][VProps.VITRAGE_STATE] = \
            OperationalResourceState.SUBOPTIMAL
        instances[3][1].entity_graph.update_vertex(instances[3][0])
        instances[3][0][VProps.STATE] = 'SUSPENDED'
        instances[3][1]._calculate_vitrage_aggregated_values(
            instances[3][0], GraphAction.UPDATE_ENTITY)

        # state and vitrage state exists and state changes
        instances[4][0][VProps.VITRAGE_STATE] = \
            OperationalResourceState.SUBOPTIMAL
        instances[4][1].entity_graph.update_vertex(instances[4][0])
        instances[4][0][VProps.STATE] = 'SUSPENDED'
        instances[4][1]._calculate_vitrage_aggregated_values(
            instances[4][0], GraphAction.UPDATE_ENTITY)

        # state and vitrage state exists and vitrage state changes
        instances[5][0][VProps.VITRAGE_STATE] = \
            OperationalResourceState.SUBOPTIMAL
        instances[5][1].entity_graph.update_vertex(instances[5][0])
        instances[5][1]._calculate_vitrage_aggregated_values(
            instances[5][0], GraphAction.UPDATE_ENTITY)

        # test assertions
        self.assertEqual('SUSPENDED',
                         instances[0][0][VProps.VITRAGE_AGGREGATED_STATE])
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         instances[0][0][VProps.VITRAGE_OPERATIONAL_STATE])
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         instances[1][0][VProps.VITRAGE_AGGREGATED_STATE])
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         instances[1][0][VProps.VITRAGE_OPERATIONAL_STATE])
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         instances[2][0][VProps.VITRAGE_AGGREGATED_STATE])
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         instances[2][0][VProps.VITRAGE_OPERATIONAL_STATE])
        self.assertEqual('SUSPENDED',
                         instances[3][0][VProps.VITRAGE_AGGREGATED_STATE])
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         instances[3][0][VProps.VITRAGE_OPERATIONAL_STATE])
        self.assertEqual('SUSPENDED',
                         instances[4][0][VProps.VITRAGE_AGGREGATED_STATE])
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         instances[4][0][VProps.VITRAGE_OPERATIONAL_STATE])
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         instances[5][0][VProps.VITRAGE_AGGREGATED_STATE])
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         instances[5][0][VProps.VITRAGE_OPERATIONAL_STATE])

    def _create_and_check_entity(self, processor=None, **kwargs):
        # create instance event with host neighbor
        (vertex, neighbors, processor) = self._create_entity(
            spec_type=self.INSTANCE_SPEC,
            datasource_action=DSAction.INIT_SNAPSHOT,
            properties=kwargs,
            processor=processor)

        # check the data in the graph is correct
        self._check_graph(processor,
                          self.NUM_VERTICES_AFTER_CREATION,
                          self.NUM_EDGES_AFTER_CREATION)

        return vertex, neighbors, processor

    def _check_graph(self,
                     processor,
                     num_vertices,
                     num_edges,
                     vertex_id=None):
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(num_vertices))

        if not vertex_id:
            self.assertEqual(num_edges, processor.entity_graph.num_edges())
        else:
            deleted_edges = processor.entity_graph.get_edges(
                vertex_id,
                attr_filter={VProps.VITRAGE_IS_DELETED: True})
            self.assertEqual(num_edges + len(deleted_edges),
                             processor.entity_graph.num_edges())
