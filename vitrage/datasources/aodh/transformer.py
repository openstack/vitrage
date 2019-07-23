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
from vitrage.datasources.aodh import AODH_DATASOURCE
from vitrage.datasources.aodh.properties import AodhEventType
from vitrage.datasources.aodh.properties import AodhProperties as AodhProps
from vitrage.datasources.aodh.properties import AodhState
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import Neighbor
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.evaluator.actions.evaluator_event_transformer \
    import VITRAGE_DATASOURCE
import vitrage.graph.utils as graph_utils
from vitrage.utils import datetime as datetime_utils


class AodhTransformer(AlarmTransformerBase):

    # Event types which need to refer them differently
    GRAPH_ACTION_MAPPING = {
        AodhEventType.DELETION: GraphAction.DELETE_ENTITY,
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
            VProps.NAME: entity_event[AodhProps.NAME],
            VProps.SEVERITY: entity_event[AodhProps.SEVERITY],
            AodhProps.DESCRIPTION: entity_event[AodhProps.DESCRIPTION],
            AodhProps.ENABLED: entity_event[AodhProps.ENABLED],
            VProps.PROJECT_ID: entity_event.get(AodhProps.PROJECT_ID, None),
            AodhProps.REPEAT_ACTIONS: entity_event[AodhProps.REPEAT_ACTIONS],
            VProps.RESOURCE_ID: entity_event[AodhProps.RESOURCE_ID],
            'alarm_type': entity_event[AodhProps.TYPE]
        }

        # TODO(annarez): convert EVENT_TYPE to tuple
        if entity_event[AodhProps.TYPE] == AodhProps.EVENT:
            metadata[AodhProps.EVENT_TYPE] = entity_event[AodhProps.EVENT_TYPE]

        elif entity_event[AodhProps.TYPE] == AodhProps.THRESHOLD:
            metadata[AodhProps.STATE_TIMESTAMP] = \
                entity_event[AodhProps.STATE_TIMESTAMP]

        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]

        update_timestamp = self._format_update_timestamp(
            AodhTransformer._timestamp(entity_event), vitrage_sample_timestamp)

        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.ALARM,
            vitrage_type=entity_event[DSProps.ENTITY_TYPE],
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_id=entity_event[AodhProps.ALARM_ID],
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
            AodhProps.DESCRIPTION: entity_event[AodhProps.DESCRIPTION],
            VProps.PROJECT_ID: entity_event[AodhProps.PROJECT_ID],
        }
        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]
        update_timestamp = self._format_update_timestamp(
            AodhTransformer._timestamp(entity_event), vitrage_sample_timestamp)

        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.ALARM,
            vitrage_type=VITRAGE_DATASOURCE,
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_id=entity_event.get(AodhProps.ALARM_ID),
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _ok_status(self, entity_event):
        return entity_event[AodhProps.STATE] != AodhState.ALARM

    def _create_entity_key(self, entity_event):
        if _is_vitrage_alarm(entity_event):
            return entity_event.get(AodhProps.VITRAGE_ID)

        entity_type = entity_event[DSProps.ENTITY_TYPE]
        alarm_id = entity_event[AodhProps.ALARM_ID]
        return tbase.build_key((EntityCategory.ALARM, entity_type, alarm_id))

    @staticmethod
    def _timestamp(entity_event):
        return datetime_utils.change_time_str_format(
            entity_event[AodhProps.TIMESTAMP],
            AodhProps.TIME_FORMAT,
            tbase.TIMESTAMP_FORMAT)

    @staticmethod
    def get_enrich_query(event):
        affected_resource_id = event.get(AodhProps.RESOURCE_ID, None)
        if not affected_resource_id:
            return None
        return {VProps.ID: affected_resource_id}

    def get_vitrage_type(self):
        return AODH_DATASOURCE


def _is_vitrage_alarm(entity_event):
    return entity_event.get(AodhProps.VITRAGE_ID) is not None
