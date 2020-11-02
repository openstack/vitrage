# Copyright 2019 - Viettel
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
from vitrage.datasources.alarm_transformer_base import \
    AlarmTransformerBase
from vitrage.datasources.kapacitor import KAPACITOR_DATASOURCE
from vitrage.datasources.kapacitor.properties import KapacitorProperties \
    as KProps
from vitrage.datasources.kapacitor.properties import KapacitorState
from vitrage.datasources import transformer_base as tbase
import vitrage.graph.utils as graph_utils

LOG = logging.getLogger(__name__)


class KapacitorTransformer(AlarmTransformerBase):

    def _create_snapshot_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_kapacitor_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_kapacitor_neighbors(entity_event)

    def _create_entity_key(self, entity_event):
        """the unique key of this entity"""
        entity_type = entity_event[DSProps.ENTITY_TYPE]
        alarm_id = entity_event[KProps.ID]
        resource_name = entity_event[KProps.RESOURCE_NAME]
        return tbase.build_key((EntityCategory.ALARM,
                                entity_type,
                                resource_name,
                                alarm_id))

    def get_vitrage_type(self):
        return KAPACITOR_DATASOURCE

    def _create_vertex(self, entity_event):
        update_timestamp = entity_event[KProps.TIME]

        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]

        update_timestamp = \
            self._format_update_timestamp(update_timestamp,
                                          vitrage_sample_timestamp)
        metadata = {
            VProps.NAME: entity_event[KProps.MESSAGE],
            VProps.SEVERITY: entity_event[KProps.PRIORITY],
            VProps.RAWTEXT: entity_event[KProps.DETAILS],
            VProps.RESOURCE_NAME: entity_event[KProps.RESOURCE_NAME],
        }

        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.ALARM,
            vitrage_type=entity_event[DSProps.ENTITY_TYPE],
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            update_timestamp=update_timestamp,
            entity_state=self._get_alarm_state(entity_event),
            metadata=metadata)

    def _ok_status(self, entity_event):
        return entity_event[KProps.PRIORITY] == KapacitorState.OK

    def _create_kapacitor_neighbors(self, entity_event):
        graph_neighbors = entity_event.get(self.QUERY_RESULT, [])
        return [self._create_neighbor(
                entity_event,
                graph_neighbor[VProps.ID],
                graph_neighbor[VProps.VITRAGE_TYPE],
                EdgeLabel.ON,
                neighbor_category=EntityCategory.RESOURCE)
                for graph_neighbor in graph_neighbors]

    @staticmethod
    def get_enrich_query(event):
        resource_type = event.get(KProps.RESOURCE_TYPE)
        resource_name = event.get(KProps.RESOURCE_NAME)

        if resource_type and resource_name:
            return {VProps.NAME: resource_name,
                    VProps.VITRAGE_TYPE: resource_type}

        return None
