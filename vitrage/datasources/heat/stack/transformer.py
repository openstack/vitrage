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

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.cinder.volume import CINDER_VOLUME_DATASOURCE
from vitrage.datasources.heat.stack import HEAT_STACK_DATASOURCE
from vitrage.datasources.heat.stack.properties import StackProperties\
    as StackProps
from vitrage.datasources.neutron.network import NEUTRON_NETWORK_DATASOURCE
from vitrage.datasources.neutron.port import NEUTRON_PORT_DATASOURCE
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.resource_transformer_base import \
    ResourceTransformerBase
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import build_key
from vitrage.datasources.transformer_base import extract_field_value
import vitrage.graph.utils as graph_utils


class HeatStackTransformer(ResourceTransformerBase):

    RESOURCE_TYPE = {
        'OS::Nova::Server': NOVA_INSTANCE_DATASOURCE,
        'OS::Cinder::Volume': CINDER_VOLUME_DATASOURCE,
        'OS::Neutron::Net': NEUTRON_NETWORK_DATASOURCE,
        'OS::Neutron::Port': NEUTRON_PORT_DATASOURCE
    }

    # graph actions which need to refer them differently
    GRAPH_ACTION_MAPPING = {
        'orchestration.stack.delete.end': GraphAction.DELETE_ENTITY,
    }

    def _create_snapshot_entity_vertex(self, entity_event):

        stack_name = extract_field_value(entity_event, StackProps.STACK_NAME)
        stack_id = extract_field_value(entity_event, StackProps.ID)
        stack_state = extract_field_value(entity_event,
                                          StackProps.STACK_STATUS)
        timestamp = extract_field_value(entity_event, StackProps.CREATION_TIME)
        project_id = extract_field_value(entity_event, StackProps.PROJECT)

        return self._create_vertex(entity_event,
                                   stack_name,
                                   stack_id,
                                   stack_state,
                                   timestamp,
                                   project_id)

    def _create_update_entity_vertex(self, entity_event):

        volume_name = extract_field_value(entity_event, StackProps.STACK_NAME)
        volume_id = extract_field_value(entity_event,
                                        StackProps.STACK_IDENTITY)
        volume_state = extract_field_value(entity_event, StackProps.STATE)
        timestamp = entity_event.get(StackProps.CREATED_AT, None)
        project_id = entity_event.get(StackProps.TENANT_ID, None)

        return self._create_vertex(entity_event,
                                   volume_name,
                                   volume_id,
                                   volume_state,
                                   timestamp,
                                   project_id)

    def _create_vertex(self,
                       entity_event,
                       stack_name,
                       stack_id,
                       stack_state,
                       update_timestamp,
                       project_id):
        metadata = {
            VProps.NAME: stack_name,
            VProps.PROJECT_ID: project_id,
        }

        entity_key = self._create_entity_key(entity_event)

        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]

        return graph_utils.create_vertex(
            entity_key,
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=HEAT_STACK_DATASOURCE,
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_id=stack_id,
            entity_state=stack_state,
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_stack_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_stack_neighbors(entity_event)

    def _create_entity_key(self, entity_event):

        is_update_event = tbase.is_update_event(entity_event)
        id_field_path = StackProps.STACK_IDENTITY\
            if is_update_event else StackProps.ID
        volume_id = extract_field_value(entity_event, id_field_path)

        key_fields = self._key_values(HEAT_STACK_DATASOURCE, volume_id)
        return build_key(key_fields)

    def _create_stack_neighbors(self, entity_event):
        neighbors = []

        for neighbor in entity_event[StackProps.RESOURCES]:
            neighbor_id = neighbor[StackProps.PHYSICAL_RESOURCE_ID]
            neighbor_datasource_type = \
                self.RESOURCE_TYPE[neighbor[StackProps.RESOURCES_TYPE]]
            neighbors.append(self._create_neighbor(entity_event,
                                                   neighbor_id,
                                                   neighbor_datasource_type,
                                                   EdgeLabel.COMPRISED,
                                                   is_entity_source=True))

        return neighbors

    def get_vitrage_type(self):
        return HEAT_STACK_DATASOURCE
