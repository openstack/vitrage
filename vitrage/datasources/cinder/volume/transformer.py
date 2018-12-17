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

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.cinder.volume import CINDER_VOLUME_DATASOURCE
from vitrage.datasources.cinder.volume.properties import \
    CinderProperties as CinderProps
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.resource_transformer_base import \
    ResourceTransformerBase
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import build_key
from vitrage.datasources.transformer_base import extract_field_value
import vitrage.graph.utils as graph_utils
from vitrage.utils.datetime import format_timestamp


class CinderVolumeTransformer(ResourceTransformerBase):

    # graph actions which need to refer them differently
    GRAPH_ACTION_MAPPING = {
        'volume.delete.end': GraphAction.DELETE_ENTITY,
        'volume.detach.start': GraphAction.DELETE_RELATIONSHIP,
        'volume.attach.end': GraphAction.UPDATE_RELATIONSHIP
    }

    def __init__(self, transformers, conf):
        super(CinderVolumeTransformer, self).__init__(transformers, conf)

    def _create_snapshot_entity_vertex(self, entity_event):

        volume_name = extract_field_value(entity_event, 'display_name')
        volume_id = extract_field_value(entity_event, 'id')
        volume_state = extract_field_value(entity_event, 'status')
        project_id = entity_event.get('os-vol-tenant-attr:tenant_id', None)
        timestamp = extract_field_value(entity_event, 'created_at')
        size = extract_field_value(entity_event, 'size')
        volume_type = extract_field_value(entity_event, 'volume_type')
        attachments = extract_field_value(entity_event, 'attachments')

        return self._create_vertex(entity_event,
                                   volume_name,
                                   volume_id,
                                   volume_state,
                                   project_id,
                                   timestamp,
                                   size,
                                   volume_type,
                                   attachments,
                                   'server_id')

    def _create_update_entity_vertex(self, entity_event):

        volume_name = extract_field_value(entity_event, 'display_name')
        volume_id = extract_field_value(entity_event, 'volume_id')
        volume_state = extract_field_value(entity_event, 'status')
        project_id = entity_event.get('tenant_id', None)
        timestamp = entity_event.get('updated_at', None)
        size = extract_field_value(entity_event, 'size')
        volume_type = extract_field_value(entity_event, 'volume_type')
        attachments = extract_field_value(entity_event, 'volume_attachment')

        return self._create_vertex(entity_event,
                                   volume_name,
                                   volume_id,
                                   volume_state,
                                   project_id,
                                   timestamp,
                                   size,
                                   volume_type,
                                   attachments,
                                   'instance_uuid')

    def _create_vertex(self,
                       entity_event,
                       volume_name,
                       volume_id,
                       volume_state,
                       project_id,
                       update_timestamp,
                       volume_size,
                       volume_type,
                       attachments,
                       server_id_key):

        server_ids = []

        for attachment in attachments:
            server_ids.append((attachment[server_id_key]))

        metadata = {
            VProps.NAME: volume_name,
            VProps.PROJECT_ID: project_id,
            CinderProps.SIZE: volume_size,
            CinderProps.VOLUME_TYPE: volume_type,
            CinderProps.ATTACHMENTS: tuple(server_ids)
        }

        entity_key = self._create_entity_key(entity_event)

        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]

        return graph_utils.create_vertex(
            entity_key,
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=CINDER_VOLUME_DATASOURCE,
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_id=volume_id,
            entity_state=volume_state,
            update_timestamp=format_timestamp(update_timestamp),
            metadata=metadata)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_volume_neighbors(entity_event,
                                             'attachments',
                                             'server_id')

    def _create_update_neighbors(self, entity_event):
        return self._create_volume_neighbors(entity_event,
                                             'volume_attachment',
                                             'instance_uuid')

    def _create_entity_key(self, entity_event):

        is_update_event = tbase.is_update_event(entity_event)
        id_field_path = 'volume_id' if is_update_event else 'id'
        volume_id = extract_field_value(entity_event, id_field_path)

        key_fields = self._key_values(CINDER_VOLUME_DATASOURCE, volume_id)
        return build_key(key_fields)

    def _create_volume_neighbors(self,
                                 entity_event,
                                 attachments_property,
                                 instance_id_property):
        neighbors = []

        for attachment in entity_event[attachments_property]:
            instance_neighbor_id = attachment[instance_id_property]
            neighbors.append(self._create_neighbor(entity_event,
                                                   instance_neighbor_id,
                                                   NOVA_INSTANCE_DATASOURCE,
                                                   EdgeLabel.ATTACHED,
                                                   is_entity_source=True))

        return neighbors

    def get_vitrage_type(self):
        return CINDER_VOLUME_DATASOURCE
