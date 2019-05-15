# Copyright 2018 - Nokia
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

from vitrage.common.constants import EdgeProperties
from vitrage.common.constants import VertexProperties
from vitrage.graph.driver.networkx_graph import NXGraph

from vitrage.entity_graph import graph_persistency
from vitrage.tests.functional.base import TestFunctionalBase
from vitrage.tests.functional.test_configuration import TestConfiguration
from vitrage.tests.mocks.graph_generator import GraphGenerator


class TestGraphPersistor(TestFunctionalBase, TestConfiguration):

    def setUp(self):
        super(TestGraphPersistor, self).setUp()
        self.conf.register_opts(self.PROCESSOR_OPTS, group='entity_graph')
        self.conf.register_opts(self.DATASOURCES_OPTS, group='datasources')
        self.add_db()
        self.load_datasources()

    def test_graph_store_and_query_recent_snapshot(self):
        g = GraphGenerator().create_graph()
        graph_persistor = graph_persistency.GraphPersistency(self._db, g)
        graph_persistor.store_graph()
        recovered_data = graph_persistor.query_recent_snapshot()
        recovered_graph = self.load_snapshot(recovered_data)
        self.assert_graph_equal(g, recovered_graph)

    def test_event_store_and_replay_events(self):
        g = GraphGenerator().create_graph()
        vertices = g.get_vertices()
        graph_persistor = graph_persistency.GraphPersistency(self._db, g)
        self.fail_msg = None
        self.event_id = 1

        def callback(pre_item,
                     current_item,
                     is_vertex,
                     graph):
            try:
                graph_persistor.persist_event(
                    pre_item, current_item, is_vertex, graph, self.event_id)
            except Exception as e:
                self.fail_msg = 'persist_event failed with exception %s' % e
            self.event_id = self.event_id + 1

        # Subscribe graph changes to callback, so events are written to db
        # after each update_vertex and update_edge callback will be called
        g.subscribe(callback)
        vertices[0][VertexProperties.VITRAGE_IS_DELETED] = True
        g.update_vertex(vertices[0])
        vertices[1][VertexProperties.VITRAGE_IS_DELETED] = True
        g.update_vertex(vertices[1])
        edge = g.get_edges(vertices[0].vertex_id).pop()
        edge[EdgeProperties.VITRAGE_IS_DELETED] = True
        g.update_edge(edge)
        graph_persistor.flush_events()

        # Store graph:
        graph_persistor.store_graph()

        # Create more events:
        vertices[2][VertexProperties.VITRAGE_IS_DELETED] = True
        g.update_vertex(vertices[2])
        vertices[3][VertexProperties.VITRAGE_IS_DELETED] = True
        g.update_vertex(vertices[3])
        edge = g.get_edges(vertices[2].vertex_id).pop()
        edge[EdgeProperties.RELATIONSHIP_TYPE] = 'kuku'
        g.update_edge(edge)
        graph_persistor.flush_events()

        self.assertIsNone(self.fail_msg, 'callback failed')

        # Reload snapshot
        recovered_data = graph_persistor.query_recent_snapshot()
        recovered_graph = self.load_snapshot(recovered_data)

        # Replay events:
        self.assertEqual(3, recovered_data.event_id, 'graph snapshot event_id')
        graph_persistor.replay_events(recovered_graph, recovered_data.event_id)

        self.assert_graph_equal(g, recovered_graph)

    @staticmethod
    def load_snapshot(data):
        return NXGraph.read_gpickle(data.graph_snapshot) if data else None
