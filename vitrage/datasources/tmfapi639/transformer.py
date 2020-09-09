# Copyright 2020
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

from oslo_log import log as logging

from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.resource_transformer_base \
    import ResourceTransformerBase
from vitrage.datasources.tmfapi639 import TMFAPI639_DATASOURCE
from vitrage.datasources import transformer_base
import vitrage.graph.utils as graph_utils

from datetime import datetime

LOG = logging.getLogger(__name__)


class TmfApi639Transformer(ResourceTransformerBase):

    def __init__(self, transformers):
        super(TmfApi639Transformer, self).__init__(transformers)

    def _create_snapshot_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_tmfapi639_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_tmfapi639_neighbors(entity_event)

    def _create_entity_key(self, entity_event):
        """the unique key of this entity"""
        entity_id = entity_event["id"]
        entity_type = TMFAPI639_DATASOURCE
        key_fields = self._key_values(entity_type, entity_id)
        return transformer_base.build_key(key_fields)

    def get_vitrage_type(self):
        return TMFAPI639_DATASOURCE

    def _create_vertex(self, entity_event):
        """Camps used from the received JSON:

        {id, name, @type ,resourceRelationship : [type, resource: id]}

        The TMF 639 API REST Endpoint can contain more information
        but we only use this one for topology.
        """
        sample_timestamp = \
            datetime.now().strftime(transformer_base.TIMESTAMP_FORMAT)
        update_timestamp = self._format_update_timestamp(
            update_timestamp=None,
            sample_timestamp=sample_timestamp)

        metadata = {
            VProps.NAME: entity_event["name"],
        }

        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=TMFAPI639_DATASOURCE,
            vitrage_sample_timestamp=sample_timestamp,
            entity_id=entity_event["id"],
            update_timestamp=update_timestamp,
            entity_state='available',
            metadata=metadata)

    def _create_tmfapi639_neighbors(self, entity_event):
        neighbors_list = []
        for n in entity_event["resourceRelationship"]:
            # create placeholder vertex
            neigh = self._create_neighbor(
                entity_event,
                n["resource"]["id"],
                TMFAPI639_DATASOURCE,
                n["type"],
                is_entity_source=True)
            neighbors_list.append(neigh)
        return neighbors_list
