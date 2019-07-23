# Copyright 2018 - Nokia, ZTE
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR  CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from oslo_log import log

from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.static.driver import StaticDriver
from vitrage.datasources.static import StaticFields
from vitrage.tests.mocks.graph_generator import GraphGenerator
from vitrage.tests.mocks.mock_graph_datasource import MOCK_DATASOURCE

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class MockDriver(StaticDriver):

    def __init__(self):
        super(StaticDriver, self).__init__()
        mock_cfg = CONF.mock_graph_datasource
        e_graph = GraphGenerator(
            networks=mock_cfg.networks,
            zones_per_cluster=mock_cfg.zones_per_cluster,
            hosts_per_zone=mock_cfg.hosts_per_zone,
            zabbix_alarms_per_host=mock_cfg.zabbix_alarms_per_host,
            instances_per_host=mock_cfg.instances_per_host,
            ports_per_instance=mock_cfg.ports_per_instance,
            volumes_per_instance=mock_cfg.volumes_per_instance,
            vitrage_alarms_per_instance=mock_cfg.vitrage_alarms_per_instance,
            tripleo_controllers=mock_cfg.tripleo_controllers,
            zabbix_alarms_per_controller=mock_cfg.zabbix_alarms_per_controller
        ).create_graph()
        definitions = e_graph.json_output_graph(raw=True)
        self.mock_entities = self._get_mock_entities(definitions)

    def get_all(self, datasource_action):
        return self.make_pickleable_iter(self.mock_entities,
                                         MOCK_DATASOURCE,
                                         datasource_action)

    def get_changes(self, datasource_action):
        return self.make_pickleable_iter([],
                                         MOCK_DATASOURCE,
                                         datasource_action)

    def _get_mock_entities(self, definitions):
        for node in definitions['nodes']:
            node[StaticFields.STATIC_ID] = str(node[VProps.GRAPH_INDEX])
            node[StaticFields.TYPE] = node[VProps.VITRAGE_TYPE]
            node[StaticFields.CATEGORY] = node[VProps.VITRAGE_CATEGORY]
            self.delete_fields(node)
        for link in definitions['links']:
            link['source'] = str(link['source'])
            link['target'] = str(link['target'])

        entities = definitions['nodes']
        relationships = definitions['links']
        return self._pack(entities, relationships)

    @staticmethod
    def delete_fields(node):
        if VProps.VITRAGE_ID in node:
            del node[VProps.VITRAGE_ID]
        if VProps.UPDATE_TIMESTAMP in node:
            del node[VProps.UPDATE_TIMESTAMP]
        if VProps.VITRAGE_CATEGORY in node:
            del node[VProps.VITRAGE_CATEGORY]
        if VProps.VITRAGE_OPERATIONAL_STATE in node:
            del node[VProps.VITRAGE_OPERATIONAL_STATE]
        if VProps.VITRAGE_SAMPLE_TIMESTAMP in node:
            del node[VProps.VITRAGE_SAMPLE_TIMESTAMP]
        if VProps.VITRAGE_AGGREGATED_STATE in node:
            del node[VProps.VITRAGE_AGGREGATED_STATE]
        if VProps.VITRAGE_IS_PLACEHOLDER in node:
            del node[VProps.VITRAGE_IS_PLACEHOLDER]
        if VProps.IS_REAL_VITRAGE_ID in node:
            del node[VProps.IS_REAL_VITRAGE_ID]
        if VProps.VITRAGE_IS_DELETED in node:
            del node[VProps.VITRAGE_IS_DELETED]
        if VProps.GRAPH_INDEX in node:
            del node[VProps.GRAPH_INDEX]
        if VProps.VITRAGE_TYPE in node:
            del node[VProps.VITRAGE_TYPE]

    @staticmethod
    def should_delete_outdated_entities():
        # Unlike the static driver (its base class), the mock datasource
        # pretends to create real entities that should not be deleted by the
        # consistency
        return False
