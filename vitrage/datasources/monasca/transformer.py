# Copyright 2018 Samsung Electronics
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.alarm_transformer_base import AlarmTransformerBase
from vitrage.datasources.monasca import MONASCA_DATASOURCE
from vitrage.datasources.monasca.properties import (
    MonascaAlarmStatuses as MAlarmStatuses)
from vitrage.datasources.monasca.properties import MonascaProperties as MProps
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import extract_field_value
import vitrage.graph.utils as graph_utils


class MonascaTransformer(AlarmTransformerBase):

    def _create_snapshot_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_vertex(self, entity_event):
        update_timestamp = entity_event[MProps.UPDATE_TIMESTAMP]
        sample_timestamp = entity_event[DSProps.SAMPLE_DATE]

        name = extract_field_value(
            entity_event, 'alarm_definition', 'name')

        metadata = {
            VProps.NAME: name,
            VProps.VITRAGE_RESOURCE_ID: entity_event[MProps.RESOURCE_ID],
            VProps.VITRAGE_RESOURCE_TYPE: entity_event[MProps.RESOURCE_TYPE],
            VProps.SEVERITY: entity_event[MProps.STATUS]
        }

        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.ALARM,
            vitrage_type=MONASCA_DATASOURCE,
            vitrage_sample_timestamp=sample_timestamp,
            entity_id=entity_event[MProps.ID],
            entity_state=self._get_alarm_state(entity_event),
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_monasca_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_monasca_neighbors(entity_event)

    def _create_monasca_neighbors(self, entity_event):
        return [self._create_neighbor(
            entity_event,
            entity_event[MProps.RESOURCE_ID],
            entity_event[MProps.RESOURCE_TYPE],
            EdgeLabel.ON,
            neighbor_category=EntityCategory.RESOURCE)]

    def _ok_status(self, entity_event):
        return entity_event[MProps.STATUS] == MAlarmStatuses.OK

    def _create_entity_key(self, entity_event):
        entity_id = entity_event[MProps.ID]
        key_fields = self._key_values(MONASCA_DATASOURCE, entity_id)
        return tbase.build_key(key_fields)

    def get_vitrage_type(self):
        return MONASCA_DATASOURCE
