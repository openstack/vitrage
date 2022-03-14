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

import json
import threading

from testtools import matchers

from vitrage.api_handler.apis.alarm import AlarmApis
from vitrage.api_handler.apis.rca import RcaApis
from vitrage.api_handler.apis.resource import ResourceApis
from vitrage.api_handler.apis.topology import TopologyApis
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EdgeProperties
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.common.utils import decompress_obj
from vitrage.datasources import NOVA_HOST_DATASOURCE
from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import NOVA_ZONE_DATASOURCE
from vitrage.datasources import OPENSTACK_CLUSTER
from vitrage.datasources.transformer_base \
    import create_cluster_placeholder_vertex
from vitrage.entity_graph.mappings.operational_alarm_severity import \
    OperationalAlarmSeverity
from vitrage.entity_graph.processor.notifier import PersistNotifier
from vitrage.graph.driver.networkx_graph import edge_copy
from vitrage.graph.driver.networkx_graph import NXGraph
import vitrage.graph.utils as graph_utils
from vitrage.persistency.service import VitragePersistorEndpoint
from vitrage.tests.base import IsEmpty
from vitrage.tests.functional.test_configuration import TestConfiguration
from vitrage.tests.unit.entity_graph.base import TestEntityGraphUnitBase
from vitrage.utils.datetime import utcnow


class TestApis(TestEntityGraphUnitBase, TestConfiguration):

    def setUp(self):
        super(TestApis, self).setUp()
        self.add_db()
        self.api_lock = threading.RLock()

    def test_get_alarms_with_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = AlarmApis(graph, self.api_lock, self._db)
        ctx = {'project_id': 'project_1', 'is_admin': True}

        # Action
        alarms = apis.get_alarms(ctx, vitrage_id='all', all_tenants=False)
        alarms = decompress_obj(alarms)['alarms']

        # Test assertions
        self.assertThat(alarms, matchers.HasLength(3))
        self._check_projects_entities(alarms, 'project_1', True)

    def test_get_alarms_with_not_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = AlarmApis(graph, self.api_lock, self._db)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        alarms = apis.get_alarms(ctx, vitrage_id='all', all_tenants=False)
        alarms = decompress_obj(alarms)['alarms']

        # Test assertions
        self.assertThat(alarms, matchers.HasLength(2))
        self._check_projects_entities(alarms, 'project_2', True)

    def test_get_alarm_counts_with_not_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = AlarmApis(graph, self.api_lock, self._db)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        counts = apis.get_alarm_counts(ctx, all_tenants=False)
        counts = json.loads(counts)

        # Test assertions
        self.assertEqual(1, counts['WARNING'])
        self.assertEqual(0, counts['SEVERE'])
        self.assertEqual(1, counts['CRITICAL'])
        self.assertEqual(0, counts['OK'])
        self.assertEqual(0, counts['N/A'])

    def test_get_alarms_with_all_tenants(self):
        # Setup
        graph = self._create_graph()
        apis = AlarmApis(graph, self.api_lock, self._db)
        ctx = {'project_id': 'project_1', 'is_admin': False}

        # Action
        alarms = apis.get_alarms(ctx, vitrage_id='all', all_tenants=True)
        alarms = decompress_obj(alarms)['alarms']

        # Test assertions
        self.assertThat(alarms, matchers.HasLength(5))
        self._check_projects_entities(alarms, None, True)

    def test_get_alarm_counts_with_all_tenants(self):
        # Setup
        graph = self._create_graph()
        apis = AlarmApis(graph, self.api_lock, self._db)
        ctx = {'project_id': 'project_1', 'is_admin': False}

        # Action
        counts = apis.get_alarm_counts(ctx, all_tenants=True)
        counts = json.loads(counts)

        # Test assertions
        self.assertEqual(2, counts['WARNING'])
        self.assertEqual(2, counts['SEVERE'])
        self.assertEqual(1, counts['CRITICAL'])
        self.assertEqual(0, counts['OK'])
        self.assertEqual(0, counts['N/A'])

    def test_get_rca_with_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = RcaApis(graph, self.api_lock, self._db)
        ctx = {'project_id': 'project_1', 'is_admin': True}

        # Action
        graph_rca = apis.get_rca(ctx, root='alarm_on_host', all_tenants=False)
        graph_rca = json.loads(graph_rca)

        # Test assertions
        self.assertThat(graph_rca['nodes'], matchers.HasLength(3))
        self._check_projects_entities(graph_rca['nodes'], 'project_1', True)

    def test_get_rca_with_not_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = RcaApis(graph, self.api_lock, self._db)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        graph_rca = apis.get_rca(ctx,
                                 root='alarm_on_instance_3',
                                 all_tenants=False)
        graph_rca = json.loads(graph_rca)

        # Test assertions
        self.assertThat(graph_rca['nodes'], matchers.HasLength(2))
        self._check_projects_entities(graph_rca['nodes'], 'project_2', True)

    def test_get_rca_with_not_admin_bla_project(self):
        # Setup
        graph = self._create_graph()
        apis = RcaApis(graph, self.api_lock, self._db)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        graph_rca = apis.get_rca(ctx, root='alarm_on_host', all_tenants=False)
        graph_rca = json.loads(graph_rca)

        # Test assertions
        self.assertThat(graph_rca['nodes'], matchers.HasLength(3))
        self._check_projects_entities(graph_rca['nodes'], 'project_2', True)

    def test_get_rca_with_all_tenants(self):
        # Setup
        graph = self._create_graph()
        apis = RcaApis(graph, self.api_lock, self._db)
        ctx = {'project_id': 'project_1', 'is_admin': False}

        # Action
        graph_rca = apis.get_rca(ctx, root='alarm_on_host', all_tenants=True)
        graph_rca = json.loads(graph_rca)

        # Test assertions
        self.assertThat(graph_rca['nodes'], matchers.HasLength(5))
        self._check_projects_entities(graph_rca['nodes'], None, True)

    def test_get_topology_with_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = TopologyApis(graph, self.api_lock)
        ctx = {'project_id': 'project_1', 'is_admin': True}

        # Action
        graph_topology = apis.get_topology(
            ctx,
            graph_type='graph',
            depth=10,
            query=None,
            root=None,
            all_tenants=False)
        graph_topology = decompress_obj(graph_topology)

        # Test assertions
        self.assertThat(graph_topology['nodes'], matchers.HasLength(8))
        self._check_projects_entities(graph_topology['nodes'],
                                      'project_1',
                                      False)

    def test_get_topology_with_not_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = TopologyApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        graph_topology = apis.get_topology(
            ctx,
            graph_type='graph',
            depth=10,
            query=None,
            root=None,
            all_tenants=False)
        graph_topology = decompress_obj(graph_topology)

        # Test assertions
        self.assertThat(graph_topology['nodes'], matchers.HasLength(7))
        self._check_projects_entities(graph_topology['nodes'],
                                      'project_2',
                                      False)

    def test_get_topology_with_all_tenants(self):
        # Setup
        graph = self._create_graph()
        apis = TopologyApis(graph, self.api_lock)
        ctx = {'project_id': 'project_1', 'is_admin': False}

        # Action
        graph_topology = apis.get_topology(
            ctx,
            graph_type='graph',
            depth=10,
            query=None,
            root=None,
            all_tenants=True)
        graph_topology = decompress_obj(graph_topology)

        # Test assertions
        self.assertThat(graph_topology['nodes'], matchers.HasLength(12))

    def test_resource_list_with_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': True}

        # Action
        resources = apis.get_resources(
            ctx,
            resource_type=None,
            all_tenants=False)
        resources = decompress_obj(resources)['resources']

        # Test assertions
        self.assertThat(resources, matchers.HasLength(5))

    def test_resource_list_with_admin_project_and_query(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': True}

        # Action
        resources = apis.get_resources(
            ctx,
            resource_type=NOVA_INSTANCE_DATASOURCE,
            all_tenants=False,
            query={'==': {'id': 'instance_3'}})
        resources = decompress_obj(resources)['resources']

        # Test assertions
        self.assertThat(resources, matchers.HasLength(1))

    def test_resource_list_with_not_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        resources = apis.get_resources(
            ctx,
            resource_type=None,
            all_tenants=False)
        resources = decompress_obj(resources)['resources']

        # Test assertions
        self.assertThat(resources, matchers.HasLength(2))

    def test_resource_list_with_not_admin_project_and_no_existing_type(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        resources = apis.get_resources(
            ctx,
            resource_type=NOVA_HOST_DATASOURCE,
            all_tenants=False)
        resources = decompress_obj(resources)['resources']

        # Test assertions
        self.assertThat(resources, IsEmpty())

    def test_resource_list_with_not_admin_project_and_existing_type(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        resources = apis.get_resources(
            ctx,
            resource_type=NOVA_INSTANCE_DATASOURCE,
            all_tenants=False)
        resources = decompress_obj(resources)['resources']

        # Test assertions
        self.assertThat(resources, matchers.HasLength(2))

    def test_resource_list_with_all_tenants(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_1', 'is_admin': False}

        # Action
        resources = apis.get_resources(
            ctx,
            resource_type=None,
            all_tenants=True)
        resources = decompress_obj(resources)['resources']

        # Test assertions
        self.assertThat(resources, matchers.HasLength(7))

    def test_resource_count_with_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': True}

        # Action
        resources = apis.count_resources(
            ctx,
            resource_type=None,
            all_tenants=False)
        resources = json.loads(resources)

        # Test assertions
        self.assertEqual(2, resources[NOVA_INSTANCE_DATASOURCE])
        self.assertEqual(1, resources[NOVA_ZONE_DATASOURCE])
        self.assertEqual(1, resources[OPENSTACK_CLUSTER])
        self.assertEqual(1, resources[NOVA_HOST_DATASOURCE])

    def test_resource_count_with_admin_project_and_query(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': True}

        # Action
        resources = apis.count_resources(
            ctx,
            resource_type=NOVA_INSTANCE_DATASOURCE,
            all_tenants=False,
            query={'==': {'id': 'instance_3'}})
        resources = json.loads(resources)

        # Test assertions
        self.assertEqual(1, resources[NOVA_INSTANCE_DATASOURCE])

    def test_resource_count_with_not_admin_project(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        resources = apis.count_resources(
            ctx,
            resource_type=None,
            all_tenants=False)
        resources = json.loads(resources)

        # Test assertions
        self.assertEqual(2, resources[NOVA_INSTANCE_DATASOURCE])

    def test_resource_count_with_not_admin_project_and_no_existing_type(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        resources = apis.count_resources(
            ctx,
            resource_type=NOVA_HOST_DATASOURCE,
            all_tenants=False)
        resources = json.loads(resources)

        # Test assertions
        self.assertThat(resources.items(), matchers.HasLength(0))

    def test_resource_count_with_not_admin_project_and_existing_type(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        resources = apis.count_resources(
            ctx,
            resource_type=NOVA_INSTANCE_DATASOURCE,
            all_tenants=False)
        resources = json.loads(resources)

        # Test assertions
        self.assertEqual(2, resources[NOVA_INSTANCE_DATASOURCE])

    def test_resource_count_with_all_tenants(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_1', 'is_admin': False}

        # Action
        resources = apis.count_resources(
            ctx,
            resource_type=None,
            all_tenants=True)
        resources = json.loads(resources)

        # Test assertions
        self.assertEqual(4, resources[NOVA_INSTANCE_DATASOURCE])
        self.assertEqual(1, resources[NOVA_ZONE_DATASOURCE])
        self.assertEqual(1, resources[OPENSTACK_CLUSTER])
        self.assertEqual(1, resources[NOVA_HOST_DATASOURCE])

    def test_resource_count_with_all_tenants_and_group_by(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_1', 'is_admin': False}

        # Action
        resources = apis.count_resources(
            ctx,
            resource_type=None,
            all_tenants=True,
            group_by=VProps.PROJECT_ID)
        resources = json.loads(resources)

        # Test assertions
        self.assertEqual(2, resources['project_1'])
        self.assertEqual(2, resources['project_2'])
        self.assertEqual(3, resources[''])

    def test_resource_show_with_admin_and_no_project_resource(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_1', 'is_admin': True}

        # Action
        resource = apis.show_resource(ctx, 'zone_1')
        resource = json.loads(resource)

        # Test assertions
        self.assertIsNotNone(resource)
        self._check_resource_properties(resource, 'zone_1',
                                        NOVA_ZONE_DATASOURCE)

    def test_resource_show_with_not_admin_and_no_project_resource(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_1', 'is_admin': False}

        # Action
        resource = apis.show_resource(ctx, 'zone_1')

        # Test assertions
        self.assertIsNone(resource)

    def test_resource_show_with_not_admin_and_resource_in_project(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_1', 'is_admin': False}

        # Action
        resource = apis.show_resource(ctx, 'instance_2')
        resource = json.loads(resource)

        # Test assertions
        self.assertIsNotNone(resource)
        self._check_resource_properties(resource, 'instance_2',
                                        NOVA_INSTANCE_DATASOURCE,
                                        project_id='project_1')

    def test_resource_show_with_not_admin_and_resource_in_other_project(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': False}

        # Action
        resource = apis.show_resource(ctx, 'instance_2')

        # Test assertions
        self.assertIsNone(resource)

    def test_resource_show_with_admin_and_resource_in_project(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_1', 'is_admin': True}

        # Action
        resource = apis.show_resource(ctx, 'instance_2')
        resource = json.loads(resource)

        # Test assertions
        self.assertIsNotNone(resource)
        self._check_resource_properties(resource, 'instance_2',
                                        NOVA_INSTANCE_DATASOURCE,
                                        project_id='project_1')

    def test_resource_show_with_admin_and_resource_in_other_project(self):
        # Setup
        graph = self._create_graph()
        apis = ResourceApis(graph, self.api_lock)
        ctx = {'project_id': 'project_2', 'is_admin': True}

        # Action
        resource = apis.show_resource(ctx, 'instance_2')
        resource = json.loads(resource)

        # Test assertions
        self.assertIsNotNone(resource)
        self._check_resource_properties(resource, 'instance_2',
                                        NOVA_INSTANCE_DATASOURCE,
                                        project_id='project_1')

    def _check_projects_entities(self,
                                 alarms,
                                 project_id,
                                 check_alarm_category):
        for alarm in alarms:
            tmp_project_id = alarm.get(VProps.PROJECT_ID, None)
            condition = True
            if check_alarm_category:
                condition = \
                    alarm[VProps.VITRAGE_CATEGORY] == EntityCategory.ALARM
            if project_id:
                condition = condition and \
                    (not tmp_project_id or
                     (tmp_project_id and tmp_project_id == project_id))
            self.assertTrue(condition)

    def _check_resource_properties(self, resource, vitrage_id,
                                   resource_type, project_id=None):
        self.assertEqual(resource[VProps.VITRAGE_ID], vitrage_id)
        self.assertEqual(resource[VProps.ID], vitrage_id)
        self.assertEqual(resource[VProps.VITRAGE_CATEGORY],
                         EntityCategory.RESOURCE)
        self.assertEqual(resource[VProps.VITRAGE_TYPE], resource_type)
        self.assertEqual(resource[VProps.STATE], 'active')
        self.assertFalse(resource[VProps.VITRAGE_IS_DELETED])
        self.assertFalse(resource[VProps.VITRAGE_IS_PLACEHOLDER])
        if project_id:
            self.assertEqual(resource[VProps.PROJECT_ID], project_id)

    def _create_graph(self):
        graph = NXGraph('Multi tenancy graph')
        self._add_alarm_persistency_subscription(graph)

        # create vertices
        cluster_vertex = create_cluster_placeholder_vertex()
        zone_vertex = self._create_resource('zone_1',
                                            NOVA_ZONE_DATASOURCE)
        host_vertex = self._create_resource('host_1',
                                            NOVA_HOST_DATASOURCE)
        instance_1_vertex = self._create_resource('instance_1',
                                                  NOVA_INSTANCE_DATASOURCE,
                                                  project_id='project_1')
        instance_2_vertex = self._create_resource('instance_2',
                                                  NOVA_INSTANCE_DATASOURCE,
                                                  project_id='project_1')
        instance_3_vertex = self._create_resource('instance_3',
                                                  NOVA_INSTANCE_DATASOURCE,
                                                  project_id='project_2')
        instance_4_vertex = self._create_resource('instance_4',
                                                  NOVA_INSTANCE_DATASOURCE,
                                                  project_id='project_2')
        alarm_on_host_vertex = self._create_alarm(
            'alarm_on_host',
            'alarm_on_host',
            metadata={VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE,
                      VProps.NAME: 'host_1',
                      VProps.RESOURCE_ID: 'host_1',
                      VProps.VITRAGE_OPERATIONAL_SEVERITY:
                          OperationalAlarmSeverity.SEVERE,
                      VProps.VITRAGE_AGGREGATED_SEVERITY:
                          OperationalAlarmSeverity.SEVERE})
        alarm_on_instance_1_vertex = self._create_alarm(
            'alarm_on_instance_1',
            'deduced_alarm',
            project_id='project_1',
            vitrage_resource_project_id='project_1',
            metadata={VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE,
                      VProps.NAME: 'instance_1',
                      VProps.RESOURCE_ID: 'sdg7849ythksjdg',
                      VProps.VITRAGE_OPERATIONAL_SEVERITY:
                          OperationalAlarmSeverity.SEVERE,
                      VProps.VITRAGE_AGGREGATED_SEVERITY:
                          OperationalAlarmSeverity.SEVERE})
        alarm_on_instance_2_vertex = self._create_alarm(
            'alarm_on_instance_2',
            'deduced_alarm',
            vitrage_resource_project_id='project_1',
            metadata={VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE,
                      VProps.NAME: 'instance_2',
                      VProps.RESOURCE_ID: 'nbfhsdugf',
                      VProps.VITRAGE_OPERATIONAL_SEVERITY:
                          OperationalAlarmSeverity.WARNING,
                      VProps.VITRAGE_AGGREGATED_SEVERITY:
                          OperationalAlarmSeverity.WARNING})
        alarm_on_instance_3_vertex = self._create_alarm(
            'alarm_on_instance_3',
            'deduced_alarm',
            project_id='project_2',
            vitrage_resource_project_id='project_2',
            metadata={VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE,
                      VProps.NAME: 'instance_3',
                      VProps.RESOURCE_ID: 'nbffhsdasdugf',
                      VProps.VITRAGE_OPERATIONAL_SEVERITY:
                          OperationalAlarmSeverity.CRITICAL,
                      VProps.VITRAGE_AGGREGATED_SEVERITY:
                          OperationalAlarmSeverity.CRITICAL})
        alarm_on_instance_4_vertex = self._create_alarm(
            'alarm_on_instance_4',
            'deduced_alarm',
            vitrage_resource_project_id='project_2',
            metadata={VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE,
                      VProps.NAME: 'instance_4',
                      VProps.RESOURCE_ID: 'ngsuy76hgd87f',
                      VProps.VITRAGE_OPERATIONAL_SEVERITY:
                          OperationalAlarmSeverity.WARNING,
                      VProps.VITRAGE_AGGREGATED_SEVERITY:
                          OperationalAlarmSeverity.WARNING})

        # create links
        edges = list()
        edges.append(graph_utils.create_edge(
            cluster_vertex.vertex_id,
            zone_vertex.vertex_id,
            EdgeLabel.CONTAINS,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            zone_vertex.vertex_id,
            host_vertex.vertex_id,
            EdgeLabel.CONTAINS,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            host_vertex.vertex_id,
            instance_1_vertex.vertex_id,
            EdgeLabel.CONTAINS,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            host_vertex.vertex_id,
            instance_2_vertex.vertex_id,
            EdgeLabel.CONTAINS,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            host_vertex.vertex_id,
            instance_3_vertex.vertex_id,
            EdgeLabel.CONTAINS,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            host_vertex.vertex_id,
            instance_4_vertex.vertex_id,
            EdgeLabel.CONTAINS,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            alarm_on_host_vertex.vertex_id,
            host_vertex.vertex_id,
            EdgeLabel.ON,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            alarm_on_instance_1_vertex.vertex_id,
            instance_1_vertex.vertex_id,
            EdgeLabel.ON,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            alarm_on_instance_2_vertex.vertex_id,
            instance_2_vertex.vertex_id,
            EdgeLabel.ON,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            alarm_on_instance_3_vertex.vertex_id,
            instance_3_vertex.vertex_id,
            EdgeLabel.ON,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            alarm_on_instance_4_vertex.vertex_id,
            instance_4_vertex.vertex_id,
            EdgeLabel.ON,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            alarm_on_host_vertex.vertex_id,
            alarm_on_instance_1_vertex.vertex_id,
            EdgeLabel.CAUSES,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            alarm_on_host_vertex.vertex_id,
            alarm_on_instance_2_vertex.vertex_id,
            EdgeLabel.CAUSES,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            alarm_on_host_vertex.vertex_id,
            alarm_on_instance_3_vertex.vertex_id,
            EdgeLabel.CAUSES,
            update_timestamp=str(utcnow())))
        edges.append(graph_utils.create_edge(
            alarm_on_host_vertex.vertex_id,
            alarm_on_instance_4_vertex.vertex_id,
            EdgeLabel.CAUSES,
            update_timestamp=str(utcnow())))

        # add vertices to graph
        graph.add_vertex(cluster_vertex)
        graph.add_vertex(zone_vertex)
        graph.add_vertex(host_vertex)
        graph.add_vertex(instance_1_vertex)
        graph.add_vertex(instance_2_vertex)
        graph.add_vertex(instance_3_vertex)
        graph.add_vertex(instance_4_vertex)
        graph.add_vertex(alarm_on_host_vertex)
        graph.add_vertex(alarm_on_instance_1_vertex)
        graph.add_vertex(alarm_on_instance_2_vertex)
        graph.add_vertex(alarm_on_instance_3_vertex)
        graph.add_vertex(alarm_on_instance_4_vertex)

        # add links to graph
        for edge in edges:
            graph.add_edge(edge)

        return graph

    def _add_alarm_persistency_subscription(self, graph):

        self._db.alarms.delete()
        self._db.changes.delete()
        self._db.edges.delete()
        persistor_endpoint = VitragePersistorEndpoint(self._db)

        def callback(before, curr, is_vertex, graph):
            notification_types = PersistNotifier._get_notification_type(
                before, curr, is_vertex)
            if not is_vertex:
                curr = edge_copy(
                    curr.source_id, curr.target_id, curr.label,
                    curr.properties)
                curr.properties[EdgeProperties.SOURCE_ID] = curr.source_id
                curr.properties[EdgeProperties.TARGET_ID] = curr.target_id

            for notification_type in notification_types:
                persistor_endpoint.process_event(notification_type,
                                                 curr.properties)

        graph.subscribe(callback)
