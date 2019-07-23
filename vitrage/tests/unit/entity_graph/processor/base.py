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

from vitrage.common.constants import VertexProperties as VProps
from vitrage.entity_graph.processor import transformer_manager
from vitrage.graph import driver as graph
from vitrage.tests.unit.entity_graph.base import TestEntityGraphUnitBase


class TestBaseProcessor(TestEntityGraphUnitBase):

    def setUp(self):
        super(TestBaseProcessor, self).setUp()
        self.load_datasources()
        self.transform = transformer_manager.TransformerManager()

    @staticmethod
    def _update_vertex_to_graph(entity_graph,
                                vitrage_category,
                                vitrage_type,
                                id_,
                                vitrage_is_deleted,
                                vitrage_is_placeholder,
                                additional_prop):
        # create vertex properties
        prop = {key: value for key, value in additional_prop.items()}
        prop[VProps.VITRAGE_CATEGORY] = vitrage_category
        prop[VProps.VITRAGE_TYPE] = vitrage_type
        prop[VProps.ID] = id_
        prop[VProps.VITRAGE_IS_DELETED] = vitrage_is_deleted
        prop[VProps.VITRAGE_IS_PLACEHOLDER] = vitrage_is_placeholder

        # TODO(Alexey): change back to original method
        # vertex_id = self.transform.get_key(prop)
        vertex_id = vitrage_category + "_" + vitrage_type + "_" + id_
        vertex = graph.Vertex(vertex_id, prop)
        entity_graph.add_vertex(vertex)

        return vertex

    @staticmethod
    def _update_edge_to_graph(entity_graph, src_id, trgt_id, label):
        edge = graph.Edge(src_id, trgt_id, label, {})
        entity_graph.add_edge(edge)
        return edge
