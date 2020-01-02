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

"""
test_vitrage graph
----------------------------------

Tests for `vitrage` graph driver
"""

from oslo_log import log as logging

from testtools import matchers

from vitrage.common.constants import EdgeProperties as EProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources import NOVA_HOST_DATASOURCE
from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import OPENSTACK_CLUSTER
from vitrage.graph import Direction
from vitrage.graph.filter import check_filter
from vitrage.graph import utils

from vitrage.tests import base
from vitrage.tests.base import IsEmpty
from vitrage.tests.unit.graph.base import ALARM
from vitrage.tests.unit.graph.base import ALARM_ON_HOST
from vitrage.tests.unit.graph.base import ALARM_ON_VM
from vitrage.tests.unit.graph.base import e_node_to_host
from vitrage.tests.unit.graph.base import GraphTestBase
from vitrage.tests.unit.graph.base import NXGraph
from vitrage.tests.unit.graph.base import RESOURCE
from vitrage.tests.unit.graph.base import v_alarm
from vitrage.tests.unit.graph.base import v_host
from vitrage.tests.unit.graph.base import v_instance
from vitrage.tests.unit.graph.base import v_node

LOG = logging.getLogger(__name__)


class TestGraph(GraphTestBase):

    def test_graph(self):
        g = NXGraph('test_graph')
        self.assertEqual('test_graph', g.name, 'graph name')
        self.assertThat(g, IsEmpty(), 'graph __len__')

        g.add_vertex(v_node)
        g.add_vertex(v_host)
        g.add_edge(e_node_to_host)
        self.assertThat(g,
                        matchers.HasLength(2),
                        'graph __len__ after add vertices')

        graph_copy = g.copy()
        self.assertEqual('test_graph', graph_copy.name, 'graph copy name')
        self.assertThat(graph_copy,
                        matchers.HasLength(2),
                        'graph copy __len__')

        g.remove_vertex(v_node)
        self.assertThat(g, matchers.HasLength(1),
                        'graph __len__ after remove vertex')
        self.assertThat(graph_copy, matchers.HasLength(2),
                        'graph copy __len__')

        updated_vertex = g.get_vertex(v_host.vertex_id)
        updated_vertex[VProps.VITRAGE_CATEGORY] = ALARM
        g.update_vertex(updated_vertex)
        v_from_g = g.get_vertex(v_host.vertex_id)
        v_from_graph_copy = graph_copy.get_vertex(v_host.vertex_id)
        self.assertEqual(ALARM, v_from_g[VProps.VITRAGE_CATEGORY],
                         'graph vertex changed after update')
        self.assertEqual(NOVA_HOST_DATASOURCE,
                         v_from_graph_copy[VProps.VITRAGE_TYPE],
                         'graph copy vertex unchanged after update')

    def test_vertex_crud(self):
        g = NXGraph('test_vertex_crud')
        g.add_vertex(v_node)
        v = g.get_vertex(v_node.vertex_id)
        self.assertEqual(v_node[VProps.ID], v[VProps.ID],
                         'vertex properties are saved')
        self.assertEqual(v_node[VProps.VITRAGE_CATEGORY],
                         v[VProps.VITRAGE_CATEGORY],
                         'vertex properties are saved')
        self.assertEqual(v_node.vertex_id, v.vertex_id,
                         'vertex vertex_id is saved')

        # Changing the referenced item
        updated_v = v
        updated_v['KUKU'] = 'KUKU'
        updated_v[VProps.VITRAGE_CATEGORY] = 'CHANGED'
        # Get it again
        v = g.get_vertex(v_node.vertex_id)
        self.assertIsNone(v.get('KUKU', None),
                          'Change should not affect graph item')
        self.assertFalse(v.get(EProps.VITRAGE_IS_DELETED, None),
                         'Change should not affect graph item')
        self.assertEqual(v_node[VProps.VITRAGE_CATEGORY],
                         v[VProps.VITRAGE_CATEGORY],
                         'Change should not affect graph item')
        # Update the graph item and see changes take place
        g.update_vertex(updated_v)
        # Get it again
        v = g.get_vertex(v_node.vertex_id)
        self.assertEqual(updated_v['KUKU'], v['KUKU'],
                         'Graph item should change after update')
        self.assertEqual(updated_v[VProps.VITRAGE_CATEGORY],
                         v[VProps.VITRAGE_CATEGORY],
                         'Graph item should change after update')

        # Update the graph item and see changes take place
        updated_v['KUKU'] = None
        g.update_vertex(updated_v)
        # Get it again
        v = g.get_vertex(v_node.vertex_id)
        self.assertNotIn('KUKU', v.properties,
                         'Update value to None should entirely remove the key')

        # check metadata
        another_vertex = utils.create_vertex(
            vitrage_id='123',
            vitrage_category=NOVA_INSTANCE_DATASOURCE,
            entity_id='456',
            metadata={'some_meta': 'DATA',
                      VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE,
                      VProps.RESOURCE_ID: 'sdg7849ythksjdg'}
        )
        g.add_vertex(another_vertex)
        v = g.get_vertex(another_vertex.vertex_id)
        self.assertEqual(another_vertex[VProps.ID], v[VProps.ID],
                         'vertex properties are saved')
        self.assertEqual(another_vertex[VProps.VITRAGE_CATEGORY],
                         v[VProps.VITRAGE_CATEGORY],
                         'vertex properties are saved')
        self.assertEqual('DATA', v['some_meta'],
                         'vertex properties are saved')
        self.assertEqual(another_vertex.vertex_id, v.vertex_id,
                         'vertex vertex_id is saved')

        # Remove the item
        g.remove_vertex(another_vertex)
        self.assertThat(g, matchers.HasLength(1),
                        'graph __len__ after remove vertex')
        v = g.get_vertex(another_vertex.vertex_id)
        self.assertIsNone(v, 'removed vertex not in graph')

    def test_update_vertices(self):

        # Test Setup
        g = NXGraph('test_update_vertices')
        g.add_vertex(v_node)
        v_node_copy = g.get_vertex(v_node.vertex_id)
        v_node_copy[VProps.NAME] = 'test_node'
        v_node_copy[VProps.VITRAGE_CATEGORY] = 'super_node'

        g.add_vertex(v_host)
        v_host_copy = g.get_vertex(v_host.vertex_id)
        v_host_copy[VProps.NAME] = 'test_host'

        # Test Action
        g.update_vertices([v_node_copy, v_host_copy])

        # Test Assertions
        updated_v_node = g.get_vertex(v_node.vertex_id)
        self.assertEqual('test_node', updated_v_node[VProps.NAME])
        self.assertEqual('super_node', updated_v_node[VProps.VITRAGE_CATEGORY])

        updated_v_host = g.get_vertex(v_host.vertex_id)
        self.assertEqual('test_host', updated_v_host[VProps.NAME])

    def test_edge_crud(self):
        g = NXGraph('test_edge_crud')
        g.add_vertex(v_node)
        g.add_vertex(v_host)
        g.add_edge(e_node_to_host)
        self.assertEqual(1, g.num_edges(), 'graph __len__ after add edge')
        label = e_node_to_host[EProps.RELATIONSHIP_TYPE]
        e = g.get_edge(v_node.vertex_id, v_host.vertex_id, label)
        self.assertEqual(e_node_to_host[EProps.RELATIONSHIP_TYPE],
                         e[EProps.RELATIONSHIP_TYPE],
                         'edge properties are saved')
        self.assertEqual(e_node_to_host.source_id, e.source_id,
                         'edge vertex_id is saved')
        self.assertEqual(e_node_to_host.target_id, e.target_id,
                         'edge vertex_id is saved')

        # Edge is correct
        v_node_neig = g.neighbors(v_node.vertex_id, direction=Direction.OUT)
        self.assertThat(v_node_neig, matchers.HasLength(1),
                        'v_node OUT neighbor count')
        self.assertEqual(v_host.vertex_id, v_node_neig.pop().vertex_id,
                         'v_node OUT neighbor is v_host')
        v_node_neig = g.neighbors(v_node.vertex_id, direction=Direction.IN)
        self.assertThat(v_node_neig, IsEmpty(), 'v_node IN neighbor count')
        v_host_neig = g.neighbors(v_host.vertex_id, direction=Direction.OUT)
        self.assertThat(v_host_neig, IsEmpty(), 'v_host OUT neighbor count')
        v_host_neig = g.neighbors(v_host.vertex_id, direction=Direction.IN)
        self.assertThat(v_host_neig, matchers.HasLength(1),
                        'v_host IN neighbor count')
        self.assertEqual(v_node.vertex_id, v_host_neig.pop().vertex_id,
                         'v_host IN neighbor is v_node')

        # Changing the referenced item
        updated_e = e
        updated_e[EProps.VITRAGE_IS_DELETED] = 'KUKU'
        updated_e[EProps.UPDATE_TIMESTAMP] = 'CHANGED'

        # Get it again
        e = g.get_edge(v_node.vertex_id, v_host.vertex_id, label)
        self.assertFalse(e.get(EProps.VITRAGE_IS_DELETED, None),
                         'Change should not affect graph item')
        self.assertEqual(e_node_to_host[EProps.UPDATE_TIMESTAMP],
                         e[EProps.UPDATE_TIMESTAMP],
                         'Change should not affect graph item')
        # Update the graph item and see changes take place
        g.update_edge(updated_e)
        # Get it again
        e = g.get_edge(v_node.vertex_id, v_host.vertex_id, label)
        self.assertEqual(updated_e[EProps.VITRAGE_IS_DELETED],
                         e[EProps.VITRAGE_IS_DELETED],
                         'Graph item should change after update')
        self.assertEqual(updated_e[EProps.UPDATE_TIMESTAMP],
                         e[EProps.UPDATE_TIMESTAMP],
                         'Graph item should change after update')

        # Update the graph item and see changes take place
        updated_e[EProps.VITRAGE_IS_DELETED] = None
        g.update_edge(updated_e)
        # Get it again
        e = g.get_edge(v_node.vertex_id, v_host.vertex_id, label)
        self.assertNotIn(EProps.VITRAGE_IS_DELETED, e.properties,
                         'Update value to None should entirely remove the key')

        # check metadata
        another_label = 'ANOTHER_LABEL'
        another_edge = utils.create_edge(
            source_id=v_node.vertex_id,
            target_id=v_host.vertex_id,
            relationship_type=another_label,
            metadata={'some_meta': 'DATA'})
        g.add_edge(another_edge)
        self.assertEqual(2, g.num_edges(), 'graph __len__ after add edge')
        e = g.get_edge(v_node.vertex_id, v_host.vertex_id, another_label)
        self.assertEqual(another_edge[EProps.RELATIONSHIP_TYPE],
                         e[EProps.RELATIONSHIP_TYPE],
                         'edge properties are saved')
        self.assertEqual('DATA', e['some_meta'],
                         'edge properties are saved')

        # Remove the item
        g.remove_edge(another_edge)
        self.assertEqual(1, g.num_edges(), 'graph __len__ after remove edge')
        e = g.get_edge(v_node.vertex_id, v_host.vertex_id, another_label)
        self.assertIsNone(e, 'removed edge not in graph')

        # Check get_edge returns None when item is missing
        edge = g.get_edge(v_host.vertex_id, 'ddd', '333')
        self.assertIsNone(edge)
        edge = g.get_edge('eee', v_node.vertex_id, '333')
        self.assertIsNone(edge)
        edge = g.get_edge(v_host.vertex_id, v_node.vertex_id, None)
        self.assertIsNone(edge)
        edge = g.get_edge(None, v_node.vertex_id, '333')
        self.assertIsNone(edge)

    def test_neighbors(self):
        relationship_a = 'RELATIONSHIP_A'
        relationship_b = 'RELATIONSHIP_B'
        relationship_c = 'RELATIONSHIP_C'

        v1 = v_node
        v2 = v_host
        v3 = v_instance
        v4 = v_alarm
        v5 = utils.create_vertex(
            vitrage_id='kuku',
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=NOVA_HOST_DATASOURCE)

        g = NXGraph('test_neighbors')
        g.add_vertex(v1)
        g.add_vertex(v2)
        g.add_vertex(v3)
        g.add_vertex(v4)
        g.add_vertex(v5)

        g.add_edge(utils.create_edge(source_id=v1.vertex_id,
                                     target_id=v2.vertex_id,
                                     relationship_type=relationship_a))
        g.add_edge(utils.create_edge(source_id=v1.vertex_id,
                                     target_id=v2.vertex_id,
                                     relationship_type=relationship_b))
        g.add_edge(utils.create_edge(source_id=v1.vertex_id,
                                     target_id=v4.vertex_id,
                                     relationship_type=relationship_a))
        g.add_edge(utils.create_edge(source_id=v1.vertex_id,
                                     target_id=v4.vertex_id,
                                     relationship_type=relationship_b))
        g.add_edge(utils.create_edge(source_id=v2.vertex_id,
                                     target_id=v1.vertex_id,
                                     relationship_type=relationship_c))
        g.add_edge(utils.create_edge(source_id=v2.vertex_id,
                                     target_id=v3.vertex_id,
                                     relationship_type=relationship_a))
        g.add_edge(utils.create_edge(source_id=v2.vertex_id,
                                     target_id=v3.vertex_id,
                                     relationship_type=relationship_b))
        g.add_edge(utils.create_edge(source_id=v2.vertex_id,
                                     target_id=v4.vertex_id,
                                     relationship_type=relationship_a))
        g.add_edge(utils.create_edge(source_id=v4.vertex_id,
                                     target_id=v1.vertex_id,
                                     relationship_type=relationship_c))

        # CHECK V1

        v1_neighbors = g.neighbors(v_id=v1.vertex_id)
        self._assert_set_equal({v2, v4}, v1_neighbors, 'Check V1 neighbors')

        v1_neighbors = g.neighbors(
            v_id=v1.vertex_id,
            vertex_attr_filter={VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE})
        self._assert_set_equal({v2}, v1_neighbors,
                               'Check V1 neighbors, vertex property filter')

        v1_neighbors = g.neighbors(
            v_id=v1.vertex_id,
            edge_attr_filter={EProps.RELATIONSHIP_TYPE: relationship_a})
        self._assert_set_equal({v2, v4}, v1_neighbors,
                               'Check V1 neighbors, edge property filter')

        v1_neighbors = g.neighbors(v_id=v1.vertex_id,
                                   direction=Direction.IN)
        self._assert_set_equal({v2, v4}, v1_neighbors,
                               'Check V1 neighbors, direction IN')

        v1_neighbors = g.neighbors(v_id=v1.vertex_id,
                                   direction=Direction.OUT)
        self._assert_set_equal({v2, v4}, v1_neighbors,
                               'Check V1 neighbors, direction OUT')

        v1_neighbors = g.neighbors(v_id=v1.vertex_id,
                                   direction=Direction.BOTH)
        self._assert_set_equal({v2, v4}, v1_neighbors,
                               'Check V1 neighbors, direction BOTH')

        v1_neighbors = g.neighbors(
            v_id=v1.vertex_id,
            direction=Direction.IN,
            edge_attr_filter={EProps.RELATIONSHIP_TYPE: relationship_c},
            vertex_attr_filter={VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE})
        self._assert_set_equal(
            {v2}, v1_neighbors,
            'Check V1 neighbors, vertex/edge property filter and direction')

        # CHECK V2

        v2_neighbors = g.neighbors(v_id=v2.vertex_id)
        self._assert_set_equal({v1, v3, v4}, v2_neighbors,
                               'Check v2 neighbors')

        v2_neighbors = g.neighbors(
            v_id=v2.vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: NOVA_HOST_DATASOURCE})
        self._assert_set_equal({}, v2_neighbors,
                               'Check v2 neighbors, vertex property filter')

        v2_neighbors = g.neighbors(
            v_id=v2.vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: [NOVA_HOST_DATASOURCE,
                                                          ALARM]})
        self._assert_set_equal({v4}, v2_neighbors,
                               'Check v2 neighbors, vertex property filter')

        v2_neighbors = g.neighbors(
            v_id=v2.vertex_id,
            edge_attr_filter={
                EProps.RELATIONSHIP_TYPE: [relationship_a, relationship_b]
            },
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: [RESOURCE, ALARM],
                VProps.VITRAGE_TYPE: [NOVA_HOST_DATASOURCE,
                                      NOVA_INSTANCE_DATASOURCE,
                                      ALARM_ON_VM,
                                      ALARM_ON_HOST]
            }
        )
        self._assert_set_equal({v3, v4}, v2_neighbors,
                               'Check v2 neighbors, edge property filter')

        # CHECK V3

        v3_neighbors = g.neighbors(v_id=v3.vertex_id, direction=Direction.OUT)
        self._assert_set_equal({}, v3_neighbors,
                               'Check v3 neighbors, direction OUT')

        v3_neighbors = g.neighbors(
            v_id=v3.vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: NOVA_HOST_DATASOURCE},
            direction=Direction.OUT)
        self._assert_set_equal({}, v3_neighbors,
                               'Check neighbors for vertex without any')
        v5_neighbors = g.neighbors(
            v_id=v5.vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: NOVA_HOST_DATASOURCE})
        self._assert_set_equal({}, v5_neighbors,
                               'Check neighbors for not connected vertex')

    def test_get_vertices(self):
        g = NXGraph('test_get_vertices')
        g.add_vertex(v_node)
        g.add_vertex(v_host)
        g.add_edge(e_node_to_host)

        all_vertices = g.get_vertices()
        self.assertThat(all_vertices, matchers.HasLength(2),
                        'get_vertices __len__ all vertices')

        node_vertices = g.get_vertices(
            vertex_attr_filter={VProps.VITRAGE_TYPE: OPENSTACK_CLUSTER})
        self.assertThat(node_vertices, matchers.HasLength(1),
                        'get_vertices __len__ node vertices')
        found_vertex = node_vertices.pop()
        self.assertEqual(OPENSTACK_CLUSTER, found_vertex[VProps.VITRAGE_TYPE],
                         'get_vertices check node vertex')

        node_vertices = g.get_vertices(
            vertex_attr_filter={VProps.VITRAGE_TYPE: OPENSTACK_CLUSTER,
                                VProps.VITRAGE_CATEGORY: RESOURCE})
        self.assertThat(node_vertices, matchers.HasLength(1),
                        'get_vertices __len__ node vertices')
        found_vertex = node_vertices.pop()
        self.assertEqual(OPENSTACK_CLUSTER, found_vertex[VProps.VITRAGE_TYPE],
                         'get_vertices check node vertex')

    def _check_callbacks_result(self, msg, exp_prev, exp_curr):

        def assert_none_or_equals(exp, act, message):
            if exp:
                self.assertEqual(exp, act, message)
            else:
                self.assertIsNone(act, message)

        self.assertIsNotNone(self.result, msg + ' Callback was not called')
        assert_none_or_equals(exp_prev, self.result[0],
                              msg + ' prev_item unexpected')
        assert_none_or_equals(exp_curr, self.result[1],
                              msg + ' curr_item unexpected')

        self.assertEqual(self.result, self.final_result,
                         'callback order is incorrect')

        self.result = None
        self.final_result = None

    def _assert_none_or_equals(self, exp, act, msg):
        if exp:
            self.assertEqual(exp, act, msg)
        else:
            self.assertIsNone(act, msg)

    # noinspection PyAttributeOutsideInit
    def test_graph_callbacks(self):

        g = NXGraph('test_graph_callbacks')
        self.result = None
        self.final_result = None

        def callback_2(pre_item, current_item, is_vertex, graph):
            # We want to make sure this callback was called ^after^ the other
            # And expect that the later callback copies the result from the
            # prior call, hence these should be equal after both were called
            self.final_result = self.result

        def callback(pre_item, current_item, is_vertex, graph):
            LOG.info('called with: pre_event_item ' + str(pre_item) +
                     ' current_item ' + str(current_item))
            self.assertIsNotNone(current_item)
            self.result = pre_item, current_item, is_vertex

        # Check there is no notification without subscribing
        g.add_vertex(v_alarm)
        self.assertIsNone(
            self.result,
            'Got notification, but add_vertex notification is not registered')

        # subscribe
        g.subscribe(callback_2, finalization=True)
        g.subscribe(callback)

        # These actions will trigger callbacks:
        g.add_vertex(v_node)
        self._check_callbacks_result('add vertex', None, v_node)

        g.add_vertex(v_host)
        self._check_callbacks_result('add vertex', None, v_host)

        g.add_edge(e_node_to_host)
        self._check_callbacks_result('add edge', None, e_node_to_host)

        updated_vertex = g.get_vertex(v_host.vertex_id)
        updated_vertex[VProps.VITRAGE_CATEGORY] = ALARM
        g.update_vertex(updated_vertex)
        self._check_callbacks_result('update vertex', v_host, updated_vertex)

        updated_edge = g.get_edge(e_node_to_host.source_id,
                                  e_node_to_host.target_id,
                                  e_node_to_host.label)
        updated_edge['ZIG'] = 'ZAG'
        g.update_edge(updated_edge)
        self._check_callbacks_result('update edge', e_node_to_host,
                                     updated_edge)

    def test_union(self):
        v1 = v_node
        v2 = v_host
        v3 = v_instance
        v4 = v_alarm

        e_v1_v2 = utils.create_edge(source_id=v1.vertex_id,
                                    target_id=v2.vertex_id,
                                    relationship_type='KUKU_v1_v2')
        e_v2_v3 = utils.create_edge(source_id=v2.vertex_id,
                                    target_id=v3.vertex_id,
                                    relationship_type='KUKU_v2_v3')
        e_v3_v4 = utils.create_edge(source_id=v3.vertex_id,
                                    target_id=v4.vertex_id,
                                    relationship_type='KUKU_v3_v4')

        g1 = NXGraph('test_union')
        g1.add_vertex(v1)
        g1.add_vertex(v2)
        g1.add_vertex(v3)
        g1.add_edge(e_v1_v2)
        g1.add_edge(e_v2_v3)

        g2 = NXGraph('test_union_')
        g2.add_vertex(v3)
        g2.add_vertex(v4)
        g2.add_edge(e_v3_v4)

        g1.union(g2)
        self.assertThat(g1, matchers.HasLength(4),
                        'incorrect graph len after union')

        e = g1.get_edge(e_v3_v4.source_id, e_v3_v4.target_id, e_v3_v4.label)
        self.assertIsNotNone(e, 'Edge missing after graphs union')

        e = g1.get_edge(e_v2_v3.source_id, e_v2_v3.target_id, e_v2_v3.label)
        self.assertIsNotNone(e, 'Edge missing after graphs union')

        e = g1.get_vertex(v3.vertex_id)
        self.assertIsNotNone(e, 'Vertex missing after graphs union')


class TestFilter(base.BaseTest):

    def test_basic_regex(self):
        event_properties = {
            "time": 121354,
            "vitrage_type": "zabbix",
            "vitrage_category": "ALARM",
            "rawtext": "Interface kukoo down on {HOST.NAME}",
            "host": "some_host_kukoo"
        }

        attr_filter = {
            "vitrage_category": "ALARM",
            "rawtext.regex": r"Interface ([_a-zA-Z0-9'\-]+) down on {"
                             "HOST.NAME}",
            "host": "some_host_kukoo"
        }
        self.assertTrue(check_filter(data=event_properties,
                                     attr_filter=attr_filter))

    def test_basic_regex_with_no_match(self):
        event_properties = {
            "time": 121354,
            "vitrage_type": "zabbix",
            "vitrage_category": "ALARM",
            "rawtext": "Text With No Match",
            "host": "some_host_kukoo"
        }

        attr_filter = {
            "vitrage_category": "ALARM",
            "rawtext.RegEx": r"Interface ([_a-zA-Z0-9'\-]+) down on {"
                             "HOST.NAME}",
            "host": "some_host_kukoo"
        }
        self.assertFalse(check_filter(data=event_properties,
                                      attr_filter=attr_filter))
