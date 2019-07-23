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

from oslo_log import log as logging

from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EdgeProperties as EProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps
from vitrage.common.exception import VitrageTransformerError
from vitrage.datasources import transformer_base
from vitrage.datasources.transformer_base import Neighbor
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.evaluator.actions.recipes.action_steps import ADD_EDGE
from vitrage.evaluator.actions.recipes.action_steps import ADD_VERTEX
from vitrage.evaluator.actions.recipes.action_steps import REMOVE_EDGE
from vitrage.evaluator.actions.recipes.action_steps import REMOVE_VERTEX
from vitrage.evaluator.actions.recipes.action_steps import UPDATE_VERTEX
from vitrage.evaluator.actions.recipes.base import EVALUATOR_EVENT_TYPE
from vitrage.evaluator.template_fields import TemplateFields as TFields
import vitrage.graph.utils as graph_utils
from vitrage.graph import Vertex


LOG = logging.getLogger(__name__)


VITRAGE_DATASOURCE = 'vitrage'


class EvaluatorEventTransformer(transformer_base.TransformerBase):

    def __init__(self, transformers):
        super(EvaluatorEventTransformer, self).__init__(transformers)
        self.actions = self._init_actions()

    def _create_snapshot_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_vertex(self, event):

        event_type = event[EVALUATOR_EVENT_TYPE]

        update_timestamp = transformer_base.convert_timestamp_format(
            '%Y-%m-%d %H:%M:%S.%f',
            event[VProps.UPDATE_TIMESTAMP]
        )

        if event_type == UPDATE_VERTEX:
            properties = {
                VProps.UPDATE_TIMESTAMP: update_timestamp,
                VProps.VITRAGE_IS_PLACEHOLDER: False,
                VProps.RESOURCE_ID: event.get(TFields.TARGET)
            }
            if VProps.IS_REAL_VITRAGE_ID in event:
                properties[VProps.IS_REAL_VITRAGE_ID] = \
                    event.get(VProps.IS_REAL_VITRAGE_ID)
            if VProps.VITRAGE_STATE in event:
                properties[VProps.VITRAGE_STATE] = \
                    event.get(VProps.VITRAGE_STATE)
            if VProps.IS_MARKED_DOWN in event:
                properties[VProps.IS_MARKED_DOWN] = \
                    event.get(VProps.IS_MARKED_DOWN)

            return Vertex(event[VProps.VITRAGE_ID], properties)

        if event_type in [ADD_VERTEX, REMOVE_VERTEX]:

            metadata = {
                VProps.NAME: event[TFields.ALARM_NAME],
                VProps.SEVERITY: event[TFields.SEVERITY],
                VProps.STATE: event[VProps.STATE],
                VProps.RESOURCE_ID: event.get(TFields.TARGET)
            }
            return graph_utils.create_vertex(
                self._create_entity_key(event),
                vitrage_category=EntityCategory.ALARM,
                vitrage_type=VITRAGE_DATASOURCE,
                vitrage_sample_timestamp=event[
                    VProps.VITRAGE_SAMPLE_TIMESTAMP],
                update_timestamp=update_timestamp,
                metadata=metadata)

        return None

    def _create_snapshot_neighbors(self, event):
        return self._create_vitrage_neighbors(event)

    def _create_update_neighbors(self, event):
        return self._create_vitrage_neighbors(event)

    def _create_vitrage_neighbors(self, event):
        event_type = event[EVALUATOR_EVENT_TYPE]

        timestamp = transformer_base.convert_timestamp_format(
            '%Y-%m-%d %H:%M:%S.%f',
            event[VProps.UPDATE_TIMESTAMP]
        )

        if event_type in [ADD_EDGE, REMOVE_EDGE]:

            relation_edge = graph_utils.create_edge(
                source_id=event[TFields.SOURCE],
                target_id=event[TFields.TARGET],
                relationship_type=event[EProps.RELATIONSHIP_TYPE],
                update_timestamp=timestamp)

            return [Neighbor(None, relation_edge)]

        if event_type == ADD_VERTEX:
            result = []

            relation_edge = graph_utils.create_edge(
                source_id=TransformerBase.uuid_from_deprecated_vitrage_id(
                    self._create_entity_key(event)),
                target_id=event[TFields.TARGET],
                relationship_type=EdgeLabel.ON,
                update_timestamp=timestamp)

            neighbor_props = {
                VProps.VITRAGE_IS_PLACEHOLDER: True,
                VProps.UPDATE_TIMESTAMP: timestamp,
                VProps.VITRAGE_SAMPLE_TIMESTAMP:
                    event[VProps.VITRAGE_SAMPLE_TIMESTAMP],
                VProps.IS_REAL_VITRAGE_ID: True,
                VProps.VITRAGE_TYPE: event.get(VProps.VITRAGE_RESOURCE_TYPE),
                VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            }
            result.append(Neighbor(
                Vertex(event[TFields.TARGET], neighbor_props), relation_edge))
            if event.get(TFields.CAUSING_ALARM):
                relation_edge = graph_utils.create_edge(
                    source_id=event[TFields.CAUSING_ALARM],
                    target_id=TransformerBase.uuid_from_deprecated_vitrage_id(
                        self._create_entity_key(event)),
                    relationship_type=EdgeLabel.CAUSES,
                    update_timestamp=timestamp)
                result.append(
                    Neighbor(Vertex(
                        event[TFields.CAUSING_ALARM],
                        {
                            VProps.UPDATE_TIMESTAMP: timestamp,
                            VProps.VITRAGE_IS_PLACEHOLDER: True,
                        }),
                        relation_edge)
                )
            return result

        return []

    def _extract_graph_action(self, event):
        event_type = event[EVALUATOR_EVENT_TYPE]

        try:
            return self.actions[event_type]
        except Exception:
            raise VitrageTransformerError(
                'Invalid Evaluator event type: (%s)' % event_type)

    @staticmethod
    def _init_actions():
        return {
            UPDATE_VERTEX: GraphAction.UPDATE_ENTITY,
            ADD_VERTEX: GraphAction.CREATE_ENTITY,
            REMOVE_VERTEX: GraphAction.DELETE_ENTITY,
            ADD_EDGE: GraphAction.UPDATE_RELATIONSHIP,
            REMOVE_EDGE: GraphAction.DELETE_RELATIONSHIP
        }

    def _create_entity_key(self, event):
        key_fields = self._key_values(event[TFields.ALARM_NAME],
                                      event[TFields.TARGET])
        return transformer_base.build_key(key_fields)

    def _key_values(self, *args):
        return (EntityCategory.ALARM, VITRAGE_DATASOURCE) + args

    def create_neighbor_placeholder_vertex(self, **kwargs):
        LOG.info('Evaluator does not create placeholders')

    def get_vitrage_type(self):
        return VITRAGE_DATASOURCE
