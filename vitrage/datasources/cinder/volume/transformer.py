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


class CinderVolumeTransformer(ResourceTransformerBase):

    # graph actions which need to refer them differently
    GRAPH_ACTION_MAPPING = {
        'volume.delete.end': GraphAction.DELETE_ENTITY,
        'volume.detach.start': GraphAction.DELETE_RELATIONSHIP,
        'volume.attach.end': GraphAction.UPDATE_RELATIONSHIP
    }

    def _create_snapshot_entity_vertex(self, entity_event):

        volume_name = extract_field_value(entity_event,
                                          CinderProps.DISPLAY_NAME)
        volume_id = extract_field_value(entity_event, CinderProps.ID)
        volume_state = extract_field_value(entity_event, CinderProps.STATUS)
        project_id = entity_event.get(
            'os-vol-tenant-attr:%s' % CinderProps.TENANT_ID, None)
        timestamp = extract_field_value(entity_event, CinderProps.CREATED_AT)
        size = extract_field_value(entity_event, CinderProps.SIZE)
        volume_type = extract_field_value(entity_event,
                                          CinderProps.VOLUME_TYPE)
        attachments = extract_field_value(entity_event,
                                          CinderProps.ATTACHMENTS)

        return self._create_vertex(entity_event,
                                   volume_name,
                                   volume_id,
                                   volume_state,
                                   project_id,
                                   timestamp,
                                   size,
                                   volume_type,
                                   attachments,
                                   CinderProps.SERVER_ID)

    def _create_update_entity_vertex(self, entity_event):

        volume_name = extract_field_value(entity_event,
                                          CinderProps.DISPLAY_NAME)
        volume_id = extract_field_value(entity_event, CinderProps.VOLUME_ID)
        volume_state = extract_field_value(entity_event, CinderProps.STATUS)
        project_id = entity_event.get(CinderProps.TENANT_ID, None)
        timestamp = entity_event.get(CinderProps.UPDATE_AT, None)
        size = extract_field_value(entity_event, CinderProps.SIZE)
        volume_type = extract_field_value(entity_event,
                                          CinderProps.VOLUME_TYPE)
        attachments = extract_field_value(entity_event,
                                          CinderProps.VOLUME_ATTACHMENT)

        return self._create_vertex(entity_event,
                                   volume_name,
                                   volume_id,
                                   volume_state,
                                   project_id,
                                   timestamp,
                                   size,
                                   volume_type,
                                   attachments,
                                   CinderProps.INSTANCE_UUID)

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
        update_timestamp = \
            self._format_update_timestamp(update_timestamp,
                                          vitrage_sample_timestamp)

        return graph_utils.create_vertex(
            entity_key,
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=CINDER_VOLUME_DATASOURCE,
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_id=volume_id,
            entity_state=volume_state,
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_volume_neighbors(entity_event,
                                             CinderProps.ATTACHMENTS,
                                             CinderProps.SERVER_ID)

    def _create_update_neighbors(self, entity_event):
        return self._create_volume_neighbors(entity_event,
                                             CinderProps.VOLUME_ATTACHMENT,
                                             CinderProps.INSTANCE_UUID)

    def _create_entity_key(self, entity_event):

        is_update_event = tbase.is_update_event(entity_event)
        id_field_path = CinderProps.VOLUME_ID \
            if is_update_event else CinderProps.ID
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
