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
test_vitrage graph algorithms
----------------------------------

Tests for `vitrage` graph driver algorithms
"""
from testtools import matchers

from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EdgeProperties as EProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.heat.stack import HEAT_STACK_DATASOURCE
from vitrage.datasources.neutron.network import NEUTRON_NETWORK_DATASOURCE
from vitrage.datasources import NOVA_HOST_DATASOURCE
from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import OPENSTACK_CLUSTER
from vitrage.datasources.transformer_base import CLUSTER_ID
from vitrage.graph.algo_driver.algorithm import Mapping
from vitrage.graph.algo_driver.sub_graph_matching import \
    NEG_CONDITION
from vitrage.graph.algo_driver.sub_graph_matching import subgraph_matching
from vitrage.graph.driver.elements import Edge
from vitrage.graph.driver.graph import Direction
from vitrage.graph.driver.networkx_graph import NXGraph
from vitrage.graph import utils as graph_utils
from vitrage.tests.base import IsEmpty
from vitrage.tests.unit.graph.base import ALARM
from vitrage.tests.unit.graph.base import ALARM_ON_HOST
from vitrage.tests.unit.graph.base import ALARM_ON_VM
from vitrage.tests.unit.graph.base import e_node_to_switch
from vitrage.tests.unit.graph.base import ELabel
from vitrage.tests.unit.graph.base import ENTITY_GRAPH_ALARMS_PER_HOST
from vitrage.tests.unit.graph.base import ENTITY_GRAPH_ALARMS_PER_VM
from vitrage.tests.unit.graph.base import ENTITY_GRAPH_HOSTS_PER_CLUSTER
from vitrage.tests.unit.graph.base import ENTITY_GRAPH_TESTS_PER_HOST
from vitrage.tests.unit.graph.base import ENTITY_GRAPH_VMS_PER_HOST
from vitrage.tests.unit.graph.base import GraphTestBase
from vitrage.tests.unit.graph.base import RESOURCE
from vitrage.tests.unit.graph.base import v_node
from vitrage.tests.unit.graph.base import v_switch

ROOT_ID = EntityCategory.RESOURCE + ':' + OPENSTACK_CLUSTER + ':' + CLUSTER_ID


class GraphAlgorithmTest(GraphTestBase):

    # noinspection PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(GraphAlgorithmTest, cls).setUpClass()
        cls.vm_id = 10000000
        cls.vm_alarm_id = 30000000
        cls.vms = []
        cls.host_alarm_id = 20000000
        cls.host_test_id = 40000000
        cls.entity_graph = cls._create_entity_graph(
            'entity_graph',
            num_of_hosts_per_node=ENTITY_GRAPH_HOSTS_PER_CLUSTER,
            num_of_vms_per_host=ENTITY_GRAPH_VMS_PER_HOST,
            num_of_alarms_per_host=ENTITY_GRAPH_ALARMS_PER_HOST,
            num_of_alarms_per_vm=ENTITY_GRAPH_ALARMS_PER_VM,
            num_of_tests_per_host=ENTITY_GRAPH_TESTS_PER_HOST)

    def test_graph_query_vertices(self):
        ga = self.entity_graph.algo

        query = {'==': {VProps.VITRAGE_TYPE: OPENSTACK_CLUSTER}}
        subgraph = ga.graph_query_vertices(root_id=ROOT_ID, query_dict=query)
        self.assertEqual(
            1,  # For Cluster
            subgraph.num_vertices(), 'num of vertex node')

        query = {
            'or': [
                {'==': {VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE}},
                {'==': {VProps.VITRAGE_TYPE: OPENSTACK_CLUSTER}}
            ]
        }

        subgraph = ga.graph_query_vertices(root_id=ROOT_ID, query_dict=query)
        self.assertEqual(
            ENTITY_GRAPH_HOSTS_PER_CLUSTER,
            subgraph.num_edges(), 'num of edges Host <-- NODE')

        query = {
            'or': [
                {'==': {VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE}},
                {'==': {VProps.VITRAGE_CATEGORY: ALARM}},
                {'==': {VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE}},
                {'==': {VProps.VITRAGE_TYPE: OPENSTACK_CLUSTER}}
            ]
        }
        subgraph = ga.graph_query_vertices(root_id=ROOT_ID, query_dict=query)
        self.assertEqual(
            ENTITY_GRAPH_HOSTS_PER_CLUSTER +
            ENTITY_GRAPH_HOSTS_PER_CLUSTER * ENTITY_GRAPH_ALARMS_PER_HOST +
            ENTITY_GRAPH_HOSTS_PER_CLUSTER * ENTITY_GRAPH_VMS_PER_HOST +
            ENTITY_GRAPH_HOSTS_PER_CLUSTER * ENTITY_GRAPH_VMS_PER_HOST *
            ENTITY_GRAPH_ALARMS_PER_VM,
            subgraph.num_edges(), 'num of BOTH edges Host (depth 1)')

        # Get first host ID
        neighboring_hosts = self.entity_graph.neighbors(
            v_node.vertex_id, {VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE})
        first_host_id = neighboring_hosts.pop().vertex_id

        query = {'!=': {'NOTHING': 'IS EVERYTHING'}}
        subgraph = ga.graph_query_vertices(
            root_id=first_host_id, query_dict=query, depth=1)
        self.assertEqual(
            1 +  # For host
            1 +  # For Cluster
            ENTITY_GRAPH_ALARMS_PER_HOST +
            ENTITY_GRAPH_TESTS_PER_HOST +
            ENTITY_GRAPH_VMS_PER_HOST,
            subgraph.num_edges(), 'num of BOTH edges Host (depth 1)')

        query = {
            'or': [
                {'==': {VProps.VITRAGE_TYPE: 'switch'}},
                {'==': {VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE}},
            ]
        }
        subgraph = ga.graph_query_vertices(
            root_id=first_host_id, query_dict=query, depth=1)
        self.assertEqual(
            1,  # For 'switch'
            subgraph.num_edges(), 'num of BOTH edges Host (depth 1)')

        subgraph = ga.graph_query_vertices(root_id=first_host_id, depth=2)
        self.assertEqual(
            1 +  # Cluster to switch
            ENTITY_GRAPH_HOSTS_PER_CLUSTER * 2 +
            ENTITY_GRAPH_ALARMS_PER_HOST +
            ENTITY_GRAPH_TESTS_PER_HOST +
            ENTITY_GRAPH_VMS_PER_HOST +
            ENTITY_GRAPH_VMS_PER_HOST * ENTITY_GRAPH_ALARMS_PER_VM,
            subgraph.num_edges(), 'num of BOTH edges Host (depth 2)')

        subgraph = ga.graph_query_vertices(root_id=first_host_id, depth=3,
                                           direction=Direction.OUT)
        self.assertEqual(
            1 +
            ENTITY_GRAPH_VMS_PER_HOST,
            subgraph.num_edges(), 'num of BOTH edges Host (depth 3)')

        query = {
            'and': [
                {'!=': {VProps.VITRAGE_TYPE: ALARM_ON_VM}},
                {'!=': {VProps.VITRAGE_TYPE: ALARM_ON_HOST}},
                {'!=': {VProps.VITRAGE_CATEGORY: ALARM}}
            ]
        }
        subgraph = ga.graph_query_vertices(root_id=ROOT_ID,
                                           query_dict=query,
                                           depth=3)
        self.assertEqual(
            1 +  # Cluster to switch
            ENTITY_GRAPH_HOSTS_PER_CLUSTER * 2 +
            ENTITY_GRAPH_HOSTS_PER_CLUSTER * ENTITY_GRAPH_TESTS_PER_HOST +
            ENTITY_GRAPH_HOSTS_PER_CLUSTER * ENTITY_GRAPH_VMS_PER_HOST,
            subgraph.num_edges(), 'num of edges Node (depth 3)')

        query = {
            'or': [
                {'==': {VProps.VITRAGE_TYPE: OPENSTACK_CLUSTER}},
                {'==': {VProps.VITRAGE_CATEGORY: ALARM}},
            ]
        }
        subgraph = ga.graph_query_vertices(root_id=ROOT_ID,
                                           query_dict=query,
                                           depth=3)
        self.assertEqual(0, subgraph.num_edges(),
                         'num of BOTH edges Node (depth 3)')
        self.assertEqual(1, subgraph.num_vertices(),
                         'num of BOTH vertices Node (depth 3)')

        # check the edge_query_dict parameter
        query = {'!=': {'NOTHING': 'IS EVERYTHING'}}
        edge_query = {'==': {EProps.RELATIONSHIP_TYPE: EdgeLabel.CONTAINS}}
        subgraph = ga.graph_query_vertices(root_id=ROOT_ID,
                                           query_dict=query,
                                           depth=5,
                                           edge_query_dict=edge_query)
        alarms = subgraph.get_vertices(
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: ALARM})
        self.assertThat(alarms, IsEmpty(), 'We filtered the ON relationship,'
                                           ' so no alarms should exist')

        # check that the vitrage_is_deleted=True edges are deleted from the
        # graph
        hosts_query = {VProps.VITRAGE_CATEGORY: RESOURCE,
                       VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE}
        hosts = self.entity_graph.get_vertices(
            vertex_attr_filter=hosts_query)
        instances_query = {VProps.VITRAGE_CATEGORY: RESOURCE,
                           VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE}
        instances = self.entity_graph.get_vertices(
            vertex_attr_filter=instances_query)
        instance_edges = self.entity_graph.get_edges(instances[0].vertex_id)

        for edge in instance_edges:
            if NOVA_HOST_DATASOURCE in edge.source_id:
                host_instance_edge = edge
        host_instance_edge[VProps.VITRAGE_IS_DELETED] = True
        self.entity_graph.update_edge(host_instance_edge)

        edges_query = {EProps.RELATIONSHIP_TYPE: EdgeLabel.CONTAINS,
                       VProps.VITRAGE_IS_DELETED: False}
        if host_instance_edge.source_id != hosts[0].vertex_id:
            new_edge = Edge(hosts[0].vertex_id, instances[0].vertex_id,
                            EdgeLabel.CONTAINS, properties=edges_query)
            self.entity_graph.update_edge(new_edge)
        else:
            new_edge = Edge(hosts[1].vertex_id, instances[0].vertex_id,
                            EdgeLabel.CONTAINS, properties=edges_query)
            self.entity_graph.update_edge(new_edge)

        query = {'!=': {'NOTHING': 'IS EVERYTHING'}}
        edge_query = {'==': {EProps.VITRAGE_IS_DELETED: False}}
        subgraph = ga.graph_query_vertices(root_id=ROOT_ID,
                                           query_dict=query,
                                           depth=5,
                                           edge_query_dict=edge_query)
        self.assertEqual(self.entity_graph.num_edges() - 1,
                         subgraph.num_edges(),
                         'We filtered the ON relationship, so no alarms '
                         'should exist')

        # Undo changes made by this test
        host_instance_edge[VProps.VITRAGE_IS_DELETED] = False
        self.entity_graph.update_edge(host_instance_edge)
        self.entity_graph.remove_edge(new_edge)

    def test_no_match_graph_query_vertices(self):
        query = {'==': {VProps.VITRAGE_TYPE: 'test'}}
        subgraph = self.entity_graph.algo.graph_query_vertices(
            root_id=ROOT_ID,
            query_dict=query)
        self.assertEqual(
            0,
            subgraph.num_vertices(), 'num of vertex node')

    def test_template_matching(self):
        """Test the template matching algorithm

        Using the entity graph (created above) as a big graph we search
        for a sub graph match
        """
        ga = self.entity_graph.algo

        # Get ids of some of the elements in the entity graph:
        vm_alarm = self.entity_graph.get_vertex(
            ALARM_ON_VM + str(self.vm_alarm_id - 1))
        host_alarm = self.entity_graph.get_vertex(
            ALARM_ON_HOST + str(self.host_alarm_id - 1))

        # Create a template for template matching
        template_graph = NXGraph('template_graph')
        t_v_host_alarm = graph_utils.create_vertex(
            vitrage_id='1', vitrage_category=ALARM, vitrage_type=ALARM_ON_HOST)
        t_v_alarm_fail = graph_utils.create_vertex(
            vitrage_id='1', vitrage_category=ALARM, vitrage_type='fail')
        t_v_host = graph_utils.create_vertex(
            vitrage_id='2',
            vitrage_category=RESOURCE,
            vitrage_type=NOVA_HOST_DATASOURCE)
        t_v_vm = graph_utils.create_vertex(
            vitrage_id='3',
            vitrage_category=RESOURCE,
            vitrage_type=NOVA_INSTANCE_DATASOURCE)
        t_v_vm_alarm = graph_utils.create_vertex(
            vitrage_id='4', vitrage_category=ALARM, vitrage_type=ALARM_ON_VM)
        t_v_switch = graph_utils.create_vertex(
            vitrage_id='5', vitrage_category=RESOURCE, vitrage_type='switch')
        t_v_node = graph_utils.create_vertex(
            vitrage_id='6',
            vitrage_category=RESOURCE,
            vitrage_type=OPENSTACK_CLUSTER)
        t_v_node_not_in_graph = graph_utils.create_vertex(
            vitrage_id='7',
            vitrage_category=RESOURCE,
            vitrage_type=OPENSTACK_CLUSTER + ' not in graph')

        e_alarm_on_host = graph_utils.create_edge(
            t_v_host_alarm.vertex_id, t_v_host.vertex_id, ELabel.ON)
        e_host_contains_vm = graph_utils.create_edge(
            t_v_host.vertex_id, t_v_vm.vertex_id, ELabel.CONTAINS)
        e_alarm_on_vm = graph_utils.create_edge(
            t_v_vm_alarm.vertex_id, t_v_vm.vertex_id, ELabel.ON)
        e_host_uses_switch = graph_utils.create_edge(
            t_v_host.vertex_id, t_v_switch.vertex_id, 'USES')
        e_node_contains_host = graph_utils.create_edge(
            t_v_node.vertex_id, t_v_host.vertex_id, ELabel.CONTAINS)
        e_node_contains_switch = graph_utils.create_edge(
            t_v_node.vertex_id, t_v_switch.vertex_id, ELabel.CONTAINS)
        e_node_contains_switch_fail = graph_utils.create_edge(
            t_v_node.vertex_id, t_v_switch.vertex_id, ELabel.CONTAINS + 'fail')
        e_host_to_node_not_in_graph = graph_utils.create_edge(
            t_v_node_not_in_graph.vertex_id, t_v_host.vertex_id, ELabel.ON)

        for v in [t_v_host_alarm, t_v_host, t_v_vm, t_v_vm_alarm,
                  t_v_switch, t_v_switch, t_v_node]:
            del(v[VProps.VITRAGE_ID])

        template_graph.add_vertex(t_v_alarm_fail)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host_alarm,
                                                 host_alarm,
                                                 is_vertex=True),
                                         validate=True)
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Single vertex alarm not in graph '
            'Template_root is a specific host alarm ')
        template_graph.remove_vertex(t_v_alarm_fail)

        template_graph.add_vertex(t_v_host_alarm)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host_alarm,
                                                 host_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Single vertex (host alarm) '
            'Template_root is a specific host alarm ')

        template_graph.add_vertex(t_v_host)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host_alarm,
                                                 host_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two disconnected vertices (host alarm , host)'
            'Template_root is a specific host alarm ')

        template_graph.add_edge(e_alarm_on_host)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host_alarm,
                                                 host_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Two connected vertices (host alarm -ON-> host)'
            ' template_root is a specific host alarm ')

        host = mappings[0][t_v_host.vertex_id]
        host_vertex = self.entity_graph.get_vertex(host.vertex_id)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host,
                                                 host_vertex,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            matchers.HasLength(ENTITY_GRAPH_ALARMS_PER_HOST),
            'Template - Two connected vertices (host alarm -ON-> host)'
            ' template_root is a specific host ')

        template_graph.add_vertex(t_v_vm)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host_alarm,
                                                 host_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two connected vertices and a disconnected vertex'
            '(host alarm -ON-> host, instance)'
            ' template_root is a specific host alarm ')

        template_graph.add_vertex(t_v_vm_alarm)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_vm_alarm,
                                                 vm_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two connected vertices and two disconnected vertices'
            '(host alarm -ON-> host, instance, instance alarm)'
            ' template_root is a specific instance alarm ')

        template_graph.add_edge(e_alarm_on_vm)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_vm_alarm,
                                                 vm_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two connected vertices and two more connected vertices'
            '(host alarm -ON-> host, instance alarm -ON-> instance)'
            ' template_root is a specific instance alarm ')

        template_graph.add_edge(e_host_contains_vm)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_vm_alarm,
                                                 vm_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            matchers.HasLength(ENTITY_GRAPH_ALARMS_PER_HOST),
            'Template - Four connected vertices'
            '(host alarm -ON-> host -CONTAINS-> instance <-ON- instance alarm)'
            ' template_root is a specific instance alarm ')

        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host_alarm,
                                                 host_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            matchers.HasLength(ENTITY_GRAPH_VMS_PER_HOST *
                               ENTITY_GRAPH_ALARMS_PER_VM),
            'Template - Four connected vertices'
            '(host alarm -ON-> host -CONTAINS-> instance <-ON- instance alarm)'
            ' template_root is a specific host alarm ')

        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host,
                                                 host_vertex,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            matchers.HasLength(ENTITY_GRAPH_VMS_PER_HOST *
                               ENTITY_GRAPH_ALARMS_PER_VM *
                               ENTITY_GRAPH_ALARMS_PER_HOST),
            'Template - Four connected vertices'
            '(host alarm -ON-> host -CONTAINS-> instance <-ON- instance alarm)'
            ' template_root is a specific host ')

        template_graph.add_vertex(t_v_switch)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_vm_alarm,
                                                 vm_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Four connected vertices and a disconnected vertex'
            '(host alarm -ON-> host -CONTAINS-> instance <-ON- instance alarm'
            ',switch) template_root is an instance alarm ')

        template_graph.add_edge(e_host_uses_switch)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_vm_alarm,
                                                 vm_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            matchers.HasLength(ENTITY_GRAPH_ALARMS_PER_HOST),
            'Template - Five connected vertices'
            '(host alarm -ON-> host -CONTAINS-> instance <-ON- instance alarm'
            ',host -USES-> switch) template_root '
            'is a specific instance alarm ')

        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host,
                                                 host_vertex,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            matchers.HasLength(ENTITY_GRAPH_VMS_PER_HOST *
                               ENTITY_GRAPH_ALARMS_PER_VM *
                               ENTITY_GRAPH_ALARMS_PER_HOST),
            'Template - Five connected vertices'
            '(host alarm -ON-> host -CONTAINS-> instance <-ON- instance alarm'
            ',host -USES-> switch) template_root is a specific host ')

        mappings = subgraph_matching(self.entity_graph, template_graph, [
            Mapping(t_v_switch, v_switch, is_vertex=True),
            Mapping(t_v_vm_alarm, vm_alarm, is_vertex=True)],
            validate=False)
        self.assertThat(
            mappings,
            matchers.HasLength(ENTITY_GRAPH_ALARMS_PER_HOST),
            'Template - Five connected vertices, two mappings given'
            '(host alarm -ON-> host -CONTAINS-> instance <-ON- instance alarm'
            ',host -USES-> switch) 7template_root is a specific host ')

        template_graph.add_vertex(t_v_node_not_in_graph)
        template_graph.add_edge(e_host_to_node_not_in_graph)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_vm_alarm,
                                                 vm_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Five connected vertices and an invalid edge'
            '(host alarm -ON-> host -CONTAINS-> instance <-ON- instance alarm'
            ',host -USES-> switch) template_root is an instance alarm ')
        template_graph.remove_vertex(t_v_node_not_in_graph)

        template_graph.remove_vertex(t_v_host_alarm)
        template_graph.add_vertex(t_v_node)
        template_graph.add_edge(e_node_contains_host)
        template_graph.add_edge(e_node_contains_switch)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_vm_alarm,
                                                 vm_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - FIVE connected vertices'
            '(host -CONTAINS-> instance <-ON- instance alarm'
            ',node -CONTAINS-> host -USES-> switch, node-CONTAINS->switch)'
            ' template_root is an instance alarm ')

        mappings = subgraph_matching(self.entity_graph, template_graph, [
            Mapping(e_node_contains_switch, e_node_to_switch, is_vertex=False),
            Mapping(t_v_vm_alarm, vm_alarm, is_vertex=True)])
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - FIVE connected vertices'
            '(host -CONTAINS-> instance <-ON- instance alarm'
            ',node -CONTAINS-> host -USES-> switch, node-CONTAINS->switch)'
            ' 3 Known Mappings[switch, node, vm alarm] ')

        template_graph.add_edge(e_node_contains_switch_fail)
        mappings = subgraph_matching(self.entity_graph, template_graph, [
            Mapping(t_v_node, v_node, is_vertex=True),
            Mapping(t_v_switch, v_switch, is_vertex=True)], validate=True)
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - FIVE connected vertices - 2 Known Mapping[node,switch]'
            ' Check that ALL edges between the 2 known mappings are checked'
            ' we now have node-CONTAINS fail->switch AND node-CONTAINS->switch'
            ' ')

        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(e_node_contains_switch,
                                                 e_node_to_switch,
                                                 is_vertex=False),
                                         validate=True)
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - FIVE connected vertices - 2 Known Mapping[node,switch]'
            ' Check that ALL edges between the 2 known mappings are checked'
            ' we now have node-CONTAINS fail->switch AND node-CONTAINS->switch'
            ' ')

        template_graph.remove_edge(e_node_contains_switch)
        mappings = subgraph_matching(self.entity_graph, template_graph, [
            Mapping(t_v_node, v_node, is_vertex=True),
            Mapping(t_v_switch, v_switch, is_vertex=True)])
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - FIVE connected vertices - 2 Known Mapping[node,switch]'
            ' But the edge between these 2 is not same as the graph '
            '(host -CONTAINS-> instance <-ON- instance alarm'
            ',node -CONTAINS-> host -USES-> switch, node-CONTAINS '
            'fail->switch)'
            ' ')

        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_vm_alarm,
                                                 vm_alarm,
                                                 is_vertex=True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - FIVE connected vertices'
            '(host -CONTAINS-> instance <-ON- instance alarm'
            ',node -CONTAINS-> host -USES-> switch, node-CONTAINS '
            'fail->switch)'
            ' template_root is an instance alarm')

    def test_template_matching_with_not_operator_of_complicated_subgraph(self):
        """Test the template matching algorithm with 'not' operator

        Using the entity graph (created above) as a big graph we search
        for a sub graph matches that has simple 'not' operator in the template
        """
        ga = self.entity_graph.algo

        # Get ids of some of the elements in the entity graph:
        host = self.entity_graph.get_vertex(
            NOVA_HOST_DATASOURCE + str(ENTITY_GRAPH_HOSTS_PER_CLUSTER - 1))

        # Create a template for template matching
        template_graph = NXGraph('template_graph')
        t_v_alarm_fail = graph_utils.create_vertex(
            vitrage_id='1', vitrage_category=ALARM, vitrage_type='fail')
        t_v_host = graph_utils.create_vertex(
            vitrage_id='2',
            vitrage_category=RESOURCE,
            vitrage_type=NOVA_HOST_DATASOURCE)
        t_v_vm = graph_utils.create_vertex(
            vitrage_id='3',
            vitrage_category=RESOURCE,
            vitrage_type=NOVA_INSTANCE_DATASOURCE)
        t_v_vm_alarm = graph_utils.create_vertex(
            vitrage_id='4', vitrage_category=ALARM, vitrage_type=ALARM_ON_VM)

        e_host_contains_vm = graph_utils.create_edge(
            t_v_host.vertex_id, t_v_vm.vertex_id, ELabel.CONTAINS)
        e_alarm_not_on_vm = graph_utils.create_edge(
            t_v_vm_alarm.vertex_id, t_v_vm.vertex_id, ELabel.ON)
        e_alarm_not_on_vm[NEG_CONDITION] = True
        e_alarm_not_on_vm[EProps.VITRAGE_IS_DELETED] = True
        e_alarm_not_on_host = graph_utils.create_edge(
            t_v_alarm_fail.vertex_id, t_v_host.vertex_id, ELabel.ON)
        e_alarm_not_on_host[NEG_CONDITION] = True
        e_alarm_not_on_host[EProps.VITRAGE_IS_DELETED] = True

        for v in [t_v_alarm_fail, t_v_host, t_v_vm, t_v_vm_alarm]:
            del(v[VProps.VITRAGE_ID])

        # add host vertex to subgraph
        template_graph.add_vertex(t_v_host)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host, host, True),
                                         validate=True)
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Single vertex alarm not in graph '
            'Template_root is a specific host ' + str(mappings))

        # add vm vertex to subgraph
        template_graph.add_vertex(t_v_vm)
        template_graph.add_edge(e_host_contains_vm)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host, host, True))
        self.assertThat(
            mappings, matchers.HasLength(ENTITY_GRAPH_VMS_PER_HOST),
            'Template - Two connected vertices (host -> vm)'
            ' template_root is a specific host ' + str(mappings))

        # add not alarm to subgraph
        template_graph.add_vertex(t_v_vm_alarm)
        template_graph.add_edge(e_alarm_not_on_vm)
        mappings = ga.sub_graph_matching(template_graph,
                                         Mapping(t_v_host, host, True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Three connected vertices (host -> vm <- NOT alarm)'
            ' template_root is a specific host ' + str(mappings))

        # create temporary entity graph
        temp_entity_graph = self.entity_graph.copy()
        temp_ga = temp_entity_graph.algo
        vms = temp_entity_graph.neighbors(
            host.vertex_id,
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE})

        ###################################################################
        # Use case 1: remove alarms of specific vm
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[0].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})
        for alarm in alarms:
            temp_entity_graph.remove_vertex(alarm)

        mappings = temp_ga.sub_graph_matching(template_graph,
                                              Mapping(t_v_host, host, True))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Three connected vertices (host -> vm <- NOT alarm)'
            'Template_root is a specific host ' + str(mappings))

        # add another not alarm to subgraph
        template_graph.add_vertex(t_v_alarm_fail)
        template_graph.add_edge(e_alarm_not_on_host)
        mappings = temp_ga.sub_graph_matching(template_graph,
                                              Mapping(t_v_host, host, True))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Four connected vertices '
            '(NOT alarm -> host -> vm <- NOT alarm)'
            ' template_root is a specific host alarm ' + str(mappings))

        ###################################################################
        # Use case 2: mark alarms and their edges as deleted
        ###################################################################
        vms = temp_entity_graph.neighbors(
            host.vertex_id,
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE})
        alarms = temp_entity_graph.neighbors(
            vms[1].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})
        for alarm in alarms:
            alarm[VProps.VITRAGE_IS_DELETED] = True
            temp_entity_graph.update_vertex(alarm)
            edges = temp_entity_graph.get_edges(alarm.vertex_id)
            for edge in edges:
                edge[EProps.VITRAGE_IS_DELETED] = True
                temp_entity_graph.update_edge(edge)

        mappings = temp_ga.sub_graph_matching(template_graph,
                                              Mapping(t_v_host, host, True))
        self.assertThat(
            mappings,
            matchers.HasLength(2),
            'Template - Three connected vertices (host -> vm <- NOT alarm)'
            'Template_root is a specific host ' + str(mappings))

        ###################################################################
        # Use case 3: mark alarm edges as deleted with event on the host
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[2].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})
        for alarm in alarms:
            edges = temp_entity_graph.get_edges(alarm.vertex_id)
            for edge in edges:
                edge[EProps.VITRAGE_IS_DELETED] = True
                temp_entity_graph.update_edge(edge)

        mappings = temp_ga.sub_graph_matching(template_graph,
                                              Mapping(t_v_host, host, True))
        self.assertThat(
            mappings,
            matchers.HasLength(3),
            'Template - Three connected vertices (host -> vm <- NOT alarm)'
            'Template_root is a specific host ' + str(mappings))

        ###################################################################
        # Use case 4: event arrived on deleted alarm vertex on vm, that
        #             has other alarms on it
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[3].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})
        deleted_vertex = alarms[0]
        deleted_vertex[VProps.VITRAGE_IS_DELETED] = True
        temp_entity_graph.update_vertex(deleted_vertex)
        mappings = temp_ga.sub_graph_matching(template_graph,
                                              Mapping(t_v_vm_alarm,
                                                      deleted_vertex,
                                                      True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Four connected vertices '
            '(NOT alarm -> host -> vm <- NOT alarm)'
            ' template_root is a specific host ' + str(mappings))

        ###################################################################
        # Use case 5: event arrived on deleted alarm edge on vm, that has
        #             other alarms on it
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[4].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})
        edges = list(temp_entity_graph.get_edges(alarms[0].vertex_id))
        deleted_edge = edges[0]
        deleted_edge[EProps.VITRAGE_IS_DELETED] = True
        temp_entity_graph.update_edge(deleted_edge)
        mappings = temp_ga.sub_graph_matching(template_graph,
                                              Mapping(e_alarm_not_on_vm,
                                                      deleted_edge,
                                                      False))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Four connected vertices '
            '(NOT alarm -> host -> vm <- NOT alarm)'
            ' template_root is a specific host ' + str(mappings))

        ###################################################################
        # Use case 6: event arrived on deleted alarm edge on vm, that has
        #             other vitrage_is_deleted alarms on it
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[5].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})
        for alarm in alarms:
            edges = temp_entity_graph.get_edges(alarm.vertex_id)
            for edge in edges:
                edge[EProps.VITRAGE_IS_DELETED] = True
                temp_entity_graph.update_edge(edge)
        deleted_edge = \
            list(temp_entity_graph.get_edges(alarms[0].vertex_id))[0]
        mappings = temp_ga.sub_graph_matching(template_graph,
                                              Mapping(e_alarm_not_on_vm,
                                                      deleted_edge,
                                                      False))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Four connected vertices '
            '(NOT alarm -> host -> vm <- NOT alarm)'
            ' template_root is a specific host ' + str(mappings))

    def test_template_matching_with_not_operator_of_simple_subgraph(self):
        """Test the template matching algorithm with 'not' operator

        Using the entity graph (created above) as a big graph we search
        for a sub graph matches that has simple 'not' operator in the template
        """
        # Get ids of some of the elements in the entity graph:
        graph_host = self.entity_graph.get_vertex(
            NOVA_HOST_DATASOURCE + str(ENTITY_GRAPH_HOSTS_PER_CLUSTER - 1))

        # Create a template for template matching
        template_graph = NXGraph('template_graph')
        t_v_vm = graph_utils.create_vertex(
            vitrage_id='1',
            vitrage_category=RESOURCE,
            vitrage_type=NOVA_INSTANCE_DATASOURCE)
        t_v_vm_alarm = graph_utils.create_vertex(
            vitrage_id='2', vitrage_category=ALARM, vitrage_type=ALARM_ON_VM)

        e_alarm_not_on_vm = graph_utils.create_edge(
            t_v_vm_alarm.vertex_id, t_v_vm.vertex_id, ELabel.ON)
        e_alarm_not_on_vm[NEG_CONDITION] = True
        e_alarm_not_on_vm[EProps.VITRAGE_IS_DELETED] = True

        for v in [t_v_vm, t_v_vm_alarm]:
            del(v[VProps.VITRAGE_ID])

        # add instance vertex to subgraph
        template_graph.add_vertex(t_v_vm)

        # add not alarm on vm vertex to subgraph
        template_graph.add_vertex(t_v_vm_alarm)
        template_graph.add_edge(e_alarm_not_on_vm)

        # create copy of the entity graph
        temp_entity_graph = self.entity_graph.copy()
        temp_ga = temp_entity_graph.algo
        vms = temp_entity_graph.neighbors(
            graph_host.vertex_id,
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE})

        ###################################################################
        # Use case 1: find subgraphs (when edges are deleted) with event on
        #             the edge
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[0].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})
        for alarm in alarms:
            edges = temp_entity_graph.get_edges(alarm.vertex_id)
            for edge in edges:
                edge[EProps.VITRAGE_IS_DELETED] = True
                temp_entity_graph.update_edge(edge)

        graph_alarm_edge = \
            list(temp_entity_graph.get_edges(alarms[0].vertex_id))[0]

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Two not connected vertices (vm <- alarm)')

        # find subgraphs (when edges are deleted) with event on the alarm
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_vm_alarm, alarms[0], True))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Two not connected vertices (vm <- alarm)')

        ###################################################################
        # Use case 2: find subgraphs (when vertices are deleted) with event
        #             on the edge
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[1].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})
        for alarm in alarms:
            alarm[VProps.VITRAGE_IS_DELETED] = True
            temp_entity_graph.update_vertex(alarm)

        graph_alarm_edge = \
            list(temp_entity_graph.get_edges(alarms[0].vertex_id))[0]

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Two not connected vertices (vm <- alarm)')

        # find subgraphs (when vertices are deleted) with event on the alarm
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_vm_alarm, alarms[0], True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        ###################################################################
        # Use case 3: find subgraphs (when vertices and edges are deleted)
        #             with event on the edge
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[2].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})
        for alarm in alarms:
            alarm[VProps.VITRAGE_IS_DELETED] = True
            temp_entity_graph.update_vertex(alarm)
            edges = temp_entity_graph.get_edges(alarm.vertex_id)
            for edge in edges:
                edge[EProps.VITRAGE_IS_DELETED] = True
                temp_entity_graph.update_edge(edge)

        graph_alarm_edge = \
            list(temp_entity_graph.get_edges(alarms[0].vertex_id))[0]

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))

        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Two not connected vertices (vm <- alarm)')

        # find subgraphs (when vertices and edges are deleted) with event
        # on the alarm
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_vm_alarm, alarms[0], True))

        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Two not connected vertices (vm <- alarm)')

        ###################################################################
        # Use case 4: find subgraphs (when one alarm of many is deleted)
        #             with event on the edge
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[3].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})
        graph_alarm = alarms[0]
        graph_alarm[VProps.VITRAGE_IS_DELETED] = True

        graph_alarm_edge = \
            list(temp_entity_graph.get_edges(alarms[0].vertex_id))[0]

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        # find subgraphs (when one alarm of many is deleted) with event
        # on the alarm
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_vm_alarm, alarms[0], True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        ###################################################################
        # Use case 5: find subgraphs (when one edge of alarm of many is
        #             deleted) with event on the edge
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[4].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})

        graph_alarm_edge = \
            list(temp_entity_graph.get_edges(alarms[0].vertex_id))[0]
        graph_alarm_edge[EProps.VITRAGE_IS_DELETED] = True
        temp_entity_graph.update_edge(graph_alarm_edge)

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))

        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        ###################################################################
        # Use case 6: find subgraphs (when one alarm its edge are deleted
        #             from many alarms) with event on the edge
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[5].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})

        alarms[0][VProps.VITRAGE_IS_DELETED] = True
        temp_entity_graph.update_vertex(alarms[0])
        graph_alarm_edge = \
            list(temp_entity_graph.get_edges(alarms[0].vertex_id))[0]
        graph_alarm_edge[EProps.VITRAGE_IS_DELETED] = True
        temp_entity_graph.update_edge(graph_alarm_edge)

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))

        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

    def test_template_matching_with_not_operator_of_problematic_subgraph(self):
        """Test the template matching algorithm with 'not' operator

        Checking the following use case:
        network -> vm <--- alarm -> stack -> network
        """

        # Get ids of some of the elements in the entity graph:
        graph_host = self.entity_graph.get_vertex(
            NOVA_HOST_DATASOURCE + str(ENTITY_GRAPH_HOSTS_PER_CLUSTER - 1))

        # Create a template for template matching
        template_graph = NXGraph('template_graph')
        t_v_network = graph_utils.create_vertex(
            vitrage_id='1',
            vitrage_category=RESOURCE,
            vitrage_type=NEUTRON_NETWORK_DATASOURCE)
        t_v_vm = graph_utils.create_vertex(
            vitrage_id='2',
            vitrage_category=RESOURCE,
            vitrage_type=NOVA_INSTANCE_DATASOURCE)
        t_v_alarm = graph_utils.create_vertex(
            vitrage_id='3', vitrage_category=ALARM, vitrage_type=ALARM_ON_VM)
        t_v_stack = graph_utils.create_vertex(
            vitrage_id='4',
            vitrage_category=RESOURCE,
            vitrage_type=HEAT_STACK_DATASOURCE)

        e_network_connect_vm = graph_utils.create_edge(
            t_v_network.vertex_id, t_v_vm.vertex_id, ELabel.CONNECT)
        e_alarm_not_on_vm = graph_utils.create_edge(
            t_v_alarm.vertex_id, t_v_vm.vertex_id, ELabel.ON)
        e_alarm_not_on_vm[NEG_CONDITION] = True
        e_alarm_not_on_vm[EProps.VITRAGE_IS_DELETED] = True
        e_alarm_on_stack = graph_utils.create_edge(
            t_v_alarm.vertex_id, t_v_stack.vertex_id, ELabel.ON)
        e_stack_connect_network = graph_utils.create_edge(
            t_v_network.vertex_id, t_v_stack.vertex_id, ELabel.CONNECT)

        for v in [t_v_vm, t_v_alarm, t_v_network, t_v_stack]:
            del(v[VProps.VITRAGE_ID])

        # add network vertex to subgraph
        template_graph.add_vertex(t_v_network)

        # add vm vertex and connect it to host
        template_graph.add_vertex(t_v_vm)
        template_graph.add_edge(e_network_connect_vm)

        # add not alarm and connect it to vm
        template_graph.add_vertex(t_v_alarm)
        template_graph.add_edge(e_alarm_not_on_vm)

        # add stack vertex and connect it to alarm
        template_graph.add_vertex(t_v_stack)
        template_graph.add_edge(e_alarm_on_stack)

        # connect stack to network
        template_graph.add_edge(e_stack_connect_network)

        # create copy of the entity graph
        temp_entity_graph = self.entity_graph.copy()
        temp_ga = temp_entity_graph.algo
        vms = temp_entity_graph.neighbors(
            graph_host.vertex_id,
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE})

        ###################################################################
        # Use case 1: alarm connected to vm
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[0].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})

        # Action
        for alarm in alarms[1:len(alarms)]:
            alarm[VProps.VITRAGE_IS_DELETED] = True
            temp_entity_graph.update_vertex(alarm)
            edges = temp_entity_graph.get_edges(alarm.vertex_id)
            for edge in edges:
                edge[EProps.VITRAGE_IS_DELETED] = True
                temp_entity_graph.update_edge(edge)

        # build problematic subgraph in entity graph
        specific_alarm = alarms[0]
        self._build_problematic_subgraph_in_entity_graph(specific_alarm,
                                                         vms[0],
                                                         temp_entity_graph,
                                                         0)

        # trigger on edge between vm and alarm
        graph_alarm_edges = \
            temp_entity_graph.get_edges(specific_alarm.vertex_id)
        for edge in graph_alarm_edges:
            if 'instance' in edge.target_id:
                graph_alarm_edge = edge

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        # trigger on alarm
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_alarm, specific_alarm, True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        ###################################################################
        # Use case 2: alarm not connected to vm (with edge
        #             vitrage_is_deleted=True)
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[1].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})

        # Action
        for alarm in alarms:
            edges = temp_entity_graph.get_edges(alarm.vertex_id)
            for edge in edges:
                edge[EProps.VITRAGE_IS_DELETED] = True
                temp_entity_graph.update_edge(edge)

        # build problematic subgraph in entity graph
        specific_alarm = alarms[0]
        self._build_problematic_subgraph_in_entity_graph(specific_alarm,
                                                         vms[1],
                                                         temp_entity_graph,
                                                         1)

        # trigger on edge between vm and alarm
        graph_alarm_edges = \
            temp_entity_graph.get_edges(specific_alarm.vertex_id)
        for edge in graph_alarm_edges:
            if 'instance' in edge.target_id:
                graph_alarm_edge = edge

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Two not connected vertices (vm <- alarm)')

        # trigger on alarm
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_alarm, specific_alarm, True))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Two not connected vertices (vm <- alarm)')

        ###################################################################
        # Use case 3: alarm not connected to vm (without any edge)
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[2].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})

        # Action
        for alarm in alarms:
            edges = temp_entity_graph.get_edges(alarm.vertex_id)
            for edge in edges:
                temp_entity_graph.remove_edge(edge)

        # build problematic subgraph in entity graph
        specific_alarm = alarms[0]
        self._build_problematic_subgraph_in_entity_graph(specific_alarm,
                                                         vms[2],
                                                         temp_entity_graph,
                                                         2)

        # trigger on edge between vm and alarm
        graph_alarm_edges = \
            temp_entity_graph.get_edges(specific_alarm.vertex_id)
        for edge in graph_alarm_edges:
            if 'instance' in edge.target_id:
                graph_alarm_edge = edge

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Two not connected vertices (vm <- alarm)')

        # trigger on alarm
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_alarm, specific_alarm, True))
        self.assertThat(
            mappings,
            matchers.HasLength(1),
            'Template - Two not connected vertices (vm <- alarm)')

        ###################################################################
        # Use case 4: alarm not connected to vm (with edge
        #             vitrage_is_deleted=True) and other connected alarms exist
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[3].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})

        # Action
        edges = [e for e in temp_entity_graph.get_edges(alarms[0].vertex_id)]
        edges[0][EProps.VITRAGE_IS_DELETED] = True
        temp_entity_graph.update_edge(edge)

        # build problematic subgraph in entity graph
        for alarm in alarms:
            self._build_problematic_subgraph_in_entity_graph(alarm,
                                                             vms[3],
                                                             temp_entity_graph,
                                                             3)

        # trigger on edge (that was deleted) between vm and alarm
        specific_alarm = alarms[0]
        graph_alarm_edges = \
            temp_entity_graph.get_edges(specific_alarm.vertex_id)
        for edge in graph_alarm_edges:
            if 'instance' in edge.target_id:
                graph_alarm_edge = edge

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        # trigger on edge (that wasn't deleted) between vm and alarm
        specific_alarm = alarms[1]
        graph_alarm_edges = \
            temp_entity_graph.get_edges(specific_alarm.vertex_id)
        for edge in graph_alarm_edges:
            if 'instance' in edge.target_id:
                graph_alarm_edge = edge

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        # trigger on alarm
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_alarm, specific_alarm, True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        # trigger on instance
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_vm, vms[3], True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        ###################################################################
        # Use case 5: alarm not connected to vm (without any edge) and
        #             other connected alarms exist
        ###################################################################
        alarms = temp_entity_graph.neighbors(
            vms[4].vertex_id,
            vertex_attr_filter={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                                VProps.VITRAGE_TYPE: ALARM_ON_VM})

        # Action
        edges = [e for e in temp_entity_graph.get_edges(alarms[0].vertex_id)]
        temp_entity_graph.remove_edge(edges[0])

        # build problematic subgraph in entity graph
        for alarm in alarms:
            self._build_problematic_subgraph_in_entity_graph(alarm,
                                                             vms[4],
                                                             temp_entity_graph,
                                                             4)

        # trigger on edge (that was deleted) between vm and alarm
        specific_alarm = alarms[0]
        graph_alarm_edges = \
            temp_entity_graph.get_edges(specific_alarm.vertex_id)
        for edge in graph_alarm_edges:
            if 'instance' in edge.target_id:
                graph_alarm_edge = edge

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        # trigger on edge (that wasn't deleted) between vm and alarm
        specific_alarm = alarms[1]
        graph_alarm_edges = \
            temp_entity_graph.get_edges(specific_alarm.vertex_id)
        for edge in graph_alarm_edges:
            if 'instance' in edge.target_id:
                graph_alarm_edge = edge

        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(e_alarm_not_on_vm, graph_alarm_edge, False))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        # trigger on alarm
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_alarm, specific_alarm, True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

        # trigger on instance
        mappings = temp_ga.sub_graph_matching(
            template_graph,
            Mapping(t_v_vm, vms[4], True))
        self.assertThat(
            mappings,
            IsEmpty(),
            'Template - Two not connected vertices (vm <- alarm)')

    @staticmethod
    def _build_problematic_subgraph_in_entity_graph(alarm,
                                                    vm,
                                                    temp_entity_graph,
                                                    num):
        stack_vertex = graph_utils.create_vertex(
            vitrage_id='stack' + str(num),
            vitrage_category=RESOURCE,
            vitrage_type=HEAT_STACK_DATASOURCE)
        temp_entity_graph.update_vertex(stack_vertex)

        alarm_stack_edge = graph_utils.create_edge(
            alarm.vertex_id, stack_vertex.vertex_id, ELabel.ON)
        temp_entity_graph.update_edge(alarm_stack_edge)

        network_vertex = graph_utils.create_vertex(
            vitrage_id='network' + str(num),
            vitrage_category=RESOURCE,
            vitrage_type=NEUTRON_NETWORK_DATASOURCE)
        temp_entity_graph.update_vertex(network_vertex)

        network_stack_edge = graph_utils.create_edge(
            network_vertex.vertex_id, stack_vertex.vertex_id, ELabel.CONNECT)
        temp_entity_graph.update_edge(network_stack_edge)

        network_vm_edge = graph_utils.create_edge(
            network_vertex.vertex_id, vm.vertex_id, ELabel.CONNECT)
        temp_entity_graph.update_edge(network_vm_edge)
