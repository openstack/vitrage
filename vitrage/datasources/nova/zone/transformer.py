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
from vitrage.datasources.nova.properties import ZoneProperties as ZoneProps
from vitrage.datasources.nova.zone import NOVA_ZONE_DATASOURCE
from vitrage.datasources import OPENSTACK_CLUSTER
from vitrage.datasources.resource_transformer_base import \
    ResourceTransformerBase
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import CLUSTER_ID
from vitrage.datasources.transformer_base import extract_field_value
import vitrage.graph.utils as graph_utils


LOG = logging.getLogger(__name__)


class ZoneTransformer(ResourceTransformerBase):

    STATE_AVAILABLE = 'available'
    STATE_UNAVAILABLE = 'unavailable'

    def _create_snapshot_entity_vertex(self, entity_event):

        zone_name = extract_field_value(entity_event, ZoneProps.ZONE_NAME)
        is_available = extract_field_value(entity_event,
                                           ZoneProps.ZONE_STATE,
                                           'available')
        state = self.STATE_AVAILABLE if is_available \
            else self.STATE_UNAVAILABLE

        return self._create_vertex(entity_event, state, zone_name)

    def _create_update_entity_vertex(self, entity_event):
        LOG.warning('Zone Update is not supported yet')

    def _create_vertex(self, entity_event, state, zone_name):

        metadata = {
            VProps.NAME: zone_name
        }
        entity_key = self._create_entity_key(entity_event)

        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]
        update_timestamp = \
            self._format_update_timestamp(None,
                                          vitrage_sample_timestamp)

        return graph_utils.create_vertex(
            entity_key,
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=NOVA_ZONE_DATASOURCE,
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_id=zone_name,
            entity_state=state,
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_zone_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_zone_neighbors(entity_event)

    def _create_zone_neighbors(self, entity_event):
        neighbors = []
        metadata = {
            VProps.VITRAGE_IS_PLACEHOLDER: False,
            VProps.STATE: 'available',
            VProps.NAME: OPENSTACK_CLUSTER
        }
        cluster_neighbor = self._create_neighbor(entity_event,
                                                 CLUSTER_ID,
                                                 OPENSTACK_CLUSTER,
                                                 EdgeLabel.CONTAINS,
                                                 is_entity_source=False,
                                                 metadata=metadata)
        neighbors.append(cluster_neighbor)

        hosts = extract_field_value(entity_event, 'hosts')

        for hostname, host_data in hosts.items():

            host_available = extract_field_value(host_data,
                                                 ZoneProps.NOVE_COMPUTE,
                                                 'available')
            host_active = extract_field_value(host_data,
                                              ZoneProps.NOVE_COMPUTE,
                                              ZoneProps.ACTIVE)

            host_state = self.STATE_AVAILABLE \
                if host_available and host_active \
                else self.STATE_UNAVAILABLE

            metadata = {
                VProps.STATE: host_state,
                VProps.VITRAGE_IS_PLACEHOLDER: False
            }

            host_neighbor = self._create_neighbor(entity_event,
                                                  hostname,
                                                  NOVA_HOST_DATASOURCE,
                                                  EdgeLabel.CONTAINS,
                                                  metadata=metadata,
                                                  is_entity_source=True)
            neighbors.append(host_neighbor)

        return neighbors

    def _create_entity_key(self, entity_event):

        zone_name = extract_field_value(entity_event, ZoneProps.ZONE_NAME)

        key_fields = self._key_values(NOVA_ZONE_DATASOURCE, zone_name)
        return tbase.build_key(key_fields)

    def get_vitrage_type(self):
        return NOVA_ZONE_DATASOURCE
