# Copyright 2018 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import itertools

import copy

from vitrage.common.constants import EdgeProperties
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources import NOVA_HOST_DATASOURCE
from vitrage.graph import Direction
from vitrage.graph.driver.networkx_graph import NXGraph
from vitrage.graph import Edge
from vitrage.graph import Vertex
from vitrage.tests.mocks import utils

RESOURCES_PATH = utils.get_resources_dir() + '/mock_configurations'


class GraphGenerator(object):
    def __init__(self,
                 networks=2,
                 zones_per_cluster=2,
                 hosts_per_zone=2,
                 zabbix_alarms_per_host=2,
                 instances_per_host=2,
                 ports_per_instance=2,
                 volumes_per_instance=2,
                 vitrage_alarms_per_instance=2,
                 tripleo_controllers=2,
                 zabbix_alarms_per_controller=2):
        self._networks = networks
        self._zones_per_cluster = zones_per_cluster
        self._hosts_per_zone = hosts_per_zone
        self._zabbix_alarms_per_host = zabbix_alarms_per_host
        self._instances_per_host = instances_per_host
        self._ports_per_instance = ports_per_instance
        self._volumes_per_instance = volumes_per_instance
        self._vitrage_alarms_per_instance = vitrage_alarms_per_instance
        self._tripleo_controllers = tripleo_controllers
        self._zabbix_alarms_per_controller = zabbix_alarms_per_controller
        self.files_cache = {}
        self.uuid_counter = 0

    def create_graph(self):
        graph = NXGraph()
        v1 = self._file_to_vertex('openstack-cluster.json')
        graph.add_vertex(v1)

        networks = self._create_n_vertices(graph,
                                           self._networks,
                                           'neutron.network.json')
        zones = self._create_n_neighbors(graph,
                                         self._zones_per_cluster,
                                         [v1],
                                         'nova.zone.json',
                                         'contains.json')
        hosts = self._create_n_neighbors(graph,
                                         self._hosts_per_zone,
                                         zones,
                                         'nova.host.json',
                                         'contains.json')
        self._create_n_neighbors(graph,
                                 self._zabbix_alarms_per_host,
                                 hosts,
                                 'zabbix.json',
                                 'on.json',
                                 Direction.IN)
        instances = self._create_n_neighbors(graph,
                                             self._instances_per_host,
                                             hosts,
                                             'nova.instance.json',
                                             'contains.json')
        ports = self._create_n_neighbors(graph,
                                         self._ports_per_instance,
                                         instances,
                                         'neutron.port.json',
                                         'attached.json',
                                         direction=Direction.IN)

        self._round_robin_edges(graph, networks, ports, 'contains.json')

        self._create_n_neighbors(graph,
                                 self._volumes_per_instance,
                                 instances,
                                 'cinder.volume.json',
                                 'attached.json',
                                 Direction.IN)
        self._create_n_neighbors(graph,
                                 self._vitrage_alarms_per_instance,
                                 instances,
                                 'vitrage.alarm.json',
                                 'on.json',
                                 Direction.IN)

        # Also create non connected components:
        tripleo_controller = \
            self._create_n_vertices(graph,
                                    self._tripleo_controllers,
                                    'tripleo.controller.json')
        self._create_n_neighbors(graph,
                                 self._zabbix_alarms_per_controller,
                                 tripleo_controller,
                                 'zabbix.json',
                                 'on.json',
                                 Direction.IN)
        return graph

    def _create_n_vertices(self, g, n, props_file):
        created_vertices = []
        for i in range(n):
            v = self._file_to_vertex(props_file, i)
            created_vertices.append(v)
            g.add_vertex(v)
        return created_vertices

    def _create_n_neighbors(self, g, n, source_v_list,
                            neighbor_props_file, neighbor_edge_props_file,
                            direction=Direction.OUT):
        created_vertices = []
        for source_v in source_v_list:
            for i in range(n):
                v = self._file_to_vertex(neighbor_props_file, i)
                v[VProps.NAME] = v[VProps.NAME] + "-" + source_v[VProps.NAME]

                if v.get(VProps.VITRAGE_TYPE) == NOVA_HOST_DATASOURCE:
                    v[VProps.ID] = v.get(VProps.NAME)

                created_vertices.append(v)
                g.add_vertex(v)
                if direction == Direction.OUT:
                    g.add_edge(self._file_to_edge(neighbor_edge_props_file,
                                                  source_v.vertex_id,
                                                  v.vertex_id))
                else:
                    g.add_edge(
                        self._file_to_edge(neighbor_edge_props_file,
                                           v.vertex_id,
                                           source_v.vertex_id))
        return created_vertices

    def _round_robin_edges(self,
                           graph,
                           source_vertices,
                           target_vertices,
                           edge_props_file):
        round_robin_source_vertices = itertools.cycle(source_vertices)
        for v in target_vertices:
            source_v = next(round_robin_source_vertices)
            graph.add_edge(self._file_to_edge(edge_props_file,
                                              source_v.vertex_id,
                                              v.vertex_id))

    def _file_to_vertex(self, filename, index=0):
        props = self._load_resource_file(filename, 'vertices')
        if props.get(VProps.ID):
            props[VProps.ID] = self.generate_mock_uuid()
        props[VProps.NAME] = "%s-%s" % (props[VProps.VITRAGE_TYPE], index)
        props[VProps.VITRAGE_ID] = self.generate_mock_uuid()
        return Vertex(props[VProps.VITRAGE_ID], props)

    def _file_to_edge(self, filename, source_id, target_id):
        props = self._load_resource_file(filename, 'edges')
        return Edge(source_id, target_id,
                    props[EdgeProperties.RELATIONSHIP_TYPE],
                    props)

    def _load_resource_file(self, filename, folder):
        full_path = RESOURCES_PATH + '/' + folder + '/'
        cache_key = (filename, folder)
        props = self.files_cache.get(cache_key, None)
        if not props:
            props = utils.load_specs(filename, full_path)
            self.files_cache[cache_key] = props
        return copy.copy(props)

    def generate_mock_uuid(self):
        self.uuid_counter = self.uuid_counter + 1
        return "11111111-1111-1111-1111-{:012d}".format(self.uuid_counter)
