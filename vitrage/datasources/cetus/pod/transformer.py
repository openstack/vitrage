# Copyright 2020 - Inspur - Qitao
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

from oslo_config import cfg
from oslo_log import log as logging

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps

from vitrage.datasources.resource_transformer_base import \
    ResourceTransformerBase
from vitrage.datasources.transformer_base import extract_field_value
import vitrage.graph.utils as graph_utils

from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import transformer_base as tbase

from vitrage.datasources.cetus.pod import CETUS_POD_DATASOURCE
from vitrage.datasources.cetus.properties import CetusPodProperties \
    as CetusProp

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class PodTransformer(ResourceTransformerBase):

    def _create_vertex(self, entity_event, state, node_name):
        metadata = {
            VProps.NAME: node_name
        }

        entity_key = self._create_entity_key(entity_event)
        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]
        update_timestamp = self._format_update_timestamp(
            extract_field_value(entity_event, DSProps.SAMPLE_DATE),
            vitrage_sample_timestamp)

        return graph_utils.create_vertex(
            entity_key,
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=CETUS_POD_DATASOURCE,
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            update_timestamp=update_timestamp,
            entity_id=extract_field_value(entity_event, CetusProp.ID),
            entity_state=state,
            metadata=metadata
        )

    def _create_snapshot_entity_vertex(self, entity_event):
        node_name = extract_field_value(entity_event, CetusProp.NAME)
        state = extract_field_value(entity_event, CetusProp.STATUS)
        return self._create_vertex(entity_event, state, node_name)

    def _create_update_entity_vertex(self, entity_event):
        node_name = extract_field_value(entity_event, CetusProp.NAME)
        state = extract_field_value(entity_event, CetusProp.STATUS)
        return self._create_vertex(entity_event, state, node_name)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_pod_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_pod_neighbors(entity_event)

    def _create_entity_key(self, event):
        instance_id = extract_field_value(event, CetusProp.ID)
        key_fields = self._key_values(
            CETUS_POD_DATASOURCE, instance_id)
        key = tbase.build_key(key_fields)
        return key

    def get_vitrage_type(self):
        return CETUS_POD_DATASOURCE

    def _create_pod_neighbors(self, entity_event):
        neighbors = []
        node = extract_field_value(entity_event, CetusProp.NODE)

        node_neighbor = self._create_neighbor(
            entity_event,
            node,
            NOVA_INSTANCE_DATASOURCE,
            EdgeLabel.CONTAINS,
            is_entity_source=False,
        )
        neighbors.append(node_neighbor)
        return neighbors
