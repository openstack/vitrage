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

from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.entity_graph.processor import processor_utils as PUtils
from vitrage.graph.driver.networkx_graph import NXGraph
from vitrage.tests.unit.entity_graph.processor import base


class TestEntityGraphManager(base.TestBaseProcessor):

    def setUp(self):
        super(TestEntityGraphManager, self).setUp()

    def test_delete_placeholder_vertex(self):
        entity_graph = NXGraph("Entity Graph")

        # create vertex properties
        vertex = self._update_vertex_to_graph(entity_graph,
                                              EntityCategory.RESOURCE,
                                              'INSTANCE',
                                              '12345',
                                              False, True, {})

        # deal with placeholder vertex
        PUtils.delete_placeholder_vertex(entity_graph, vertex)
        vertex = entity_graph.get_vertex(vertex.vertex_id)
        self.assertTrue(vertex is None)

        # create vertex properties
        vertex = self._update_vertex_to_graph(entity_graph,
                                              EntityCategory.RESOURCE,
                                              'INSTANCE',
                                              '12345',
                                              False, False, {})

        # deal with non placeholder vertex
        PUtils.delete_placeholder_vertex(entity_graph, vertex)
        vertex = entity_graph.get_vertex(vertex.vertex_id)
        self.assertTrue(vertex is not None)

    def test_mark_vertex_as_deleted(self):
        entity_graph = NXGraph("Entity Graph")

        # create vertex properties
        vertex = self._update_vertex_to_graph(entity_graph,
                                              EntityCategory.RESOURCE,
                                              'INSTANCE',
                                              '12345',
                                              False, True, {})

        # check vitrage deleted
        self.assertFalse(PUtils.is_deleted(vertex))
        PUtils.mark_deleted(entity_graph, vertex)
        self.assertTrue(PUtils.is_deleted(vertex))

    def test_mark_edge_as_deleted(self):
        entity_graph = NXGraph("Entity Graph")

        # create vertex properties

        vertex1 = self._update_vertex_to_graph(entity_graph,
                                               EntityCategory.RESOURCE,
                                               'HOST',
                                               '54321',
                                               False, True, {})
        vertex2 = self._update_vertex_to_graph(entity_graph,
                                               EntityCategory.RESOURCE,
                                               'INSTANCE',
                                               '12345',
                                               False, True, {})
        edge = self._update_edge_to_graph(entity_graph,
                                          vertex1.vertex_id,
                                          vertex2.vertex_id,
                                          EdgeLabel.CONTAINS)

        # check vitrage deleted
        self.assertFalse(PUtils.is_deleted(edge))
        PUtils.mark_deleted(entity_graph, edge)
        self.assertTrue(PUtils.is_deleted(edge))

    def test_find_neighbor_types(self):
        neighbors = []
        entity_graph = NXGraph("Entity Graph")
        entities_details = \
            [(EntityCategory.RESOURCE, 'HOST', '1', False, True),
             (EntityCategory.RESOURCE, 'STORAGE', '2', False, True),
             (EntityCategory.RESOURCE, 'APPLICATION', '3', False, True),
             (EntityCategory.RESOURCE, 'STORAGE', '4', False, True),
             (EntityCategory.ALARM, 'INSTANCE_AT_RISK', '5', False, True)]

        # add neighbors
        for details in entities_details:
            # neighbor
            vertex = self._update_vertex_to_graph(entity_graph, details[0],
                                                  details[1], details[2],
                                                  details[3], details[4], {})
            neighbors.append((vertex, None))

        # get neighbors types
        types = PUtils.find_neighbor_types(neighbors)
        self.assertThat(types, matchers.HasLength(4))
