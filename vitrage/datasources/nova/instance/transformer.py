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

from oslo_config import cfg
from oslo_log import log as logging

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.instance.field_extractor import \
    LegacyNotificationFieldExtractor
from vitrage.datasources.nova.instance.field_extractor import \
    SnapshotEventFieldExtractor
from vitrage.datasources.nova.instance.field_extractor import \
    VersionedNotificationFieldExtractor
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.resource_transformer_base import \
    ResourceTransformerBase
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import extract_field_value
import vitrage.graph.utils as graph_utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class InstanceTransformer(ResourceTransformerBase):

    snapshot_extractor = SnapshotEventFieldExtractor()
    legacy_notifications_extractor = LegacyNotificationFieldExtractor()
    versioned_notifications_extractor = VersionedNotificationFieldExtractor()

    # graph actions which need to refer them differently
    GRAPH_ACTION_MAPPING = {
        'compute.instance.delete.end': GraphAction.DELETE_ENTITY,
        'instance.delete.end': GraphAction.DELETE_ENTITY,
    }

    def _create_snapshot_entity_vertex(self, entity_event):
        LOG.debug('got snapshot')
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        LOG.debug('got event: %s', entity_event[DSProps.EVENT_TYPE])
        return self._create_vertex(entity_event)

    def _create_vertex(self, entity_event):
        field_extractor = self._get_field_extractor(entity_event)
        if not field_extractor:
            LOG.warning('Failed to identify event type for event: %s',
                        entity_event)
            return

        metadata = {
            VProps.NAME: field_extractor.name(entity_event),
            VProps.PROJECT_ID: field_extractor.tenant_id(entity_event),
            'host_id': field_extractor.host(entity_event)
        }

        instance_name = field_extractor.instance_name(entity_event)
        if instance_name:
            metadata['instance_name'] = instance_name

        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]

        # TODO(Alexey): need to check that only the UPDATE datasource_action
        # will update the UPDATE_TIMESTAMP property
        update_timestamp = self._format_update_timestamp(
            extract_field_value(entity_event, DSProps.SAMPLE_DATE),
            vitrage_sample_timestamp)

        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=NOVA_INSTANCE_DATASOURCE,
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_id=field_extractor.entity_id(entity_event),
            entity_state=field_extractor.state(entity_event),
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_instance_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_instance_neighbors(entity_event)

    def _create_instance_neighbors(self, entity_event):
        field_extractor = self._get_field_extractor(entity_event)
        if not field_extractor:
            LOG.warning('Failed to identify event type for event: %s',
                        entity_event)
            return []

        host_name = field_extractor.host(entity_event)

        host_neighbor = self._create_neighbor(entity_event,
                                              host_name,
                                              NOVA_HOST_DATASOURCE,
                                              EdgeLabel.CONTAINS,
                                              is_entity_source=False)

        return [host_neighbor]

    def _create_entity_key(self, event):
        LOG.debug('Creating key for instance event: %s', event)

        instance_id = self._get_field_extractor(event).entity_id(event)
        key_fields = self._key_values(NOVA_INSTANCE_DATASOURCE, instance_id)
        key = tbase.build_key(key_fields)

        LOG.debug('Created key: %s', key)

        return key

    def get_vitrage_type(self):
        return NOVA_INSTANCE_DATASOURCE

    def _get_field_extractor(self, event):
        """Return an object that extracts the field values from the event"""
        if tbase.is_update_event(event):
            return self.versioned_notifications_extractor if \
                CONF.use_nova_versioned_notifications is True else \
                self.legacy_notifications_extractor
        else:
            return self.snapshot_extractor
