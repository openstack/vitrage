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
from vitrage.datasources.alarm_transformer_base import AlarmTransformerBase
from vitrage.datasources.ceilometer import CEILOMETER_DATASOURCE
from vitrage.datasources.ceilometer.properties \
    import CeilometerEventType as CeilEventType
from vitrage.datasources.ceilometer.properties \
    import CeilometerProperties as CeilProps
from vitrage.datasources.ceilometer.properties \
    import CeilometerState as CeilState
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import Neighbor
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.evaluator.actions.evaluator_event_transformer \
    import VITRAGE_DATASOURCE
import vitrage.graph.utils as graph_utils
from vitrage.utils import datetime as datetime_utils


class CeilometerTransformer(AlarmTransformerBase):

    # Event types which need to refer them differently
    GRAPH_ACTION_MAPPING = {
        CeilEventType.DELETION: GraphAction.DELETE_ENTITY,
    }

    def _create_snapshot_entity_vertex(self, entity_event):
        if _is_vitrage_alarm(entity_event):
            return self._create_merge_alarm_vertex(entity_event)
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        if _is_vitrage_alarm(entity_event):
            return self._create_merge_alarm_vertex(entity_event)
        return self._create_vertex(entity_event)

    def _create_vertex(self, entity_event):
        metadata = {
            VProps.NAME: entity_event[CeilProps.NAME],
            VProps.SEVERITY: entity_event[CeilProps.SEVERITY],
            CeilProps.DESCRIPTION: entity_event[CeilProps.DESCRIPTION],
            CeilProps.ENABLED: entity_event[CeilProps.ENABLED],
            VProps.PROJECT_ID: entity_event.get(CeilProps.PROJECT_ID, None),
            CeilProps.REPEAT_ACTIONS: entity_event[CeilProps.REPEAT_ACTIONS],
            VProps.RESOURCE_ID: entity_event[CeilProps.RESOURCE_ID],
            'alarm_type': entity_event[CeilProps.TYPE]
        }

        # TODO(annarez): convert EVENT_TYPE to tuple
        if entity_event[CeilProps.TYPE] == CeilProps.EVENT:
            metadata[CeilProps.EVENT_TYPE] = \
                entity_event[CeilProps.EVENT_TYPE]

        elif entity_event[CeilProps.TYPE] == CeilProps.THRESHOLD:
            metadata[CeilProps.STATE_TIMESTAMP] = \
                entity_event[CeilProps.STATE_TIMESTAMP]

        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]

        update_timestamp = self._format_update_timestamp(
            CeilometerTransformer._timestamp(entity_event),
            vitrage_sample_timestamp)

        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.ALARM,
            vitrage_type=entity_event[DSProps.ENTITY_TYPE],
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_id=entity_event[CeilProps.ALARM_ID],
            entity_state=self._get_alarm_state(entity_event),
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_aodh_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_aodh_neighbors(entity_event)

    def _create_aodh_neighbors(self, entity_event):
        graph_neighbors = entity_event.get(self.QUERY_RESULT, [])
        result = []
        for vertex in graph_neighbors:
            edge = graph_utils.create_edge(
                source_id=TransformerBase.uuid_from_deprecated_vitrage_id(
                    self._create_entity_key(entity_event)),
                target_id=vertex.vertex_id,
                relationship_type=EdgeLabel.ON)
            result.append(Neighbor(vertex, edge))
        return result

    def _create_merge_alarm_vertex(self, entity_event):
        """Handle an alarm that already has a vitrage_id

        This is a deduced alarm created in aodh by vitrage, so it already
        exists in the graph.
        This function will update the exiting vertex (and not create a new one)
        """
        metadata = {
            CeilProps.DESCRIPTION: entity_event[CeilProps.DESCRIPTION],
            VProps.PROJECT_ID: entity_event[CeilProps.PROJECT_ID],
        }
        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]
        update_timestamp = self._format_update_timestamp(
            CeilometerTransformer._timestamp(entity_event),
            vitrage_sample_timestamp)

        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.ALARM,
            vitrage_type=VITRAGE_DATASOURCE,
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_id=entity_event.get(CeilProps.ALARM_ID),
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _ok_status(self, entity_event):
        return entity_event[CeilProps.STATE] != CeilState.ALARM

    def _create_entity_key(self, entity_event):
        if _is_vitrage_alarm(entity_event):
            return entity_event.get(CeilProps.VITRAGE_ID)

        entity_type = entity_event[DSProps.ENTITY_TYPE]
        alarm_id = entity_event[CeilProps.ALARM_ID]
        return tbase.build_key((EntityCategory.ALARM, entity_type, alarm_id))

    @staticmethod
    def _timestamp(entity_event):
        return datetime_utils.change_time_str_format(
            entity_event[CeilProps.TIMESTAMP],
            CeilProps.TIME_FORMAT,
            tbase.TIMESTAMP_FORMAT)

    @staticmethod
    def get_enrich_query(event):
        affected_resource_id = event.get(CeilProps.RESOURCE_ID, None)
        if not affected_resource_id:
            return None
        return {VProps.ID: affected_resource_id}

    def get_vitrage_type(self):
        return CEILOMETER_DATASOURCE


def _is_vitrage_alarm(entity_event):
    return entity_event.get(CeilProps.VITRAGE_ID) is not None
