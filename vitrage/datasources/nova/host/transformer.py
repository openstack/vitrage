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

from oslo_log import log as logging

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.properties import HostProperties as HostProps
from vitrage.datasources.nova.zone import NOVA_ZONE_DATASOURCE
from vitrage.datasources.resource_transformer_base import \
    ResourceTransformerBase
from vitrage.datasources import transformer_base
from vitrage.datasources.transformer_base import extract_field_value
import vitrage.graph.utils as graph_utils


LOG = logging.getLogger(__name__)


class HostTransformer(ResourceTransformerBase):

    def _create_snapshot_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event,
                                   entity_event.get(HostProps.HOST))

    def _create_update_entity_vertex(self, entity_event):
        LOG.warning('Host Update is not supported yet')

    def _create_vertex(self, entity_event, host_name):

        metadata = {VProps.NAME: host_name}
        entity_key = self._create_entity_key(entity_event)

        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]
        update_timestamp = \
            self._format_update_timestamp(None,
                                          vitrage_sample_timestamp)

        return graph_utils.create_vertex(
            entity_key,
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=NOVA_HOST_DATASOURCE,
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_id=host_name,
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_host_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_host_neighbors(entity_event)

    def _create_host_neighbors(self, entity_event):
        zone_name = extract_field_value(entity_event, HostProps.ZONE)
        zone_neighbor = self._create_neighbor(entity_event,
                                              zone_name,
                                              NOVA_ZONE_DATASOURCE,
                                              EdgeLabel.CONTAINS,
                                              is_entity_source=False)
        return [zone_neighbor]

    def _create_entity_key(self, entity_event):
        key_fields = self._key_values(NOVA_HOST_DATASOURCE,
                                      entity_event.get(HostProps.HOST))
        return transformer_base.build_key(key_fields)

    def get_vitrage_type(self):
        return NOVA_HOST_DATASOURCE
