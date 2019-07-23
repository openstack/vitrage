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
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.consistency import CONSISTENCY_DATASOURCE
from vitrage.datasources.resource_transformer_base import \
    ResourceTransformerBase
import vitrage.graph.utils as graph_utils


class ConsistencyTransformer(ResourceTransformerBase):

    # graph actions which need to refer them differently
    GRAPH_ACTION_MAPPING = {
        GraphAction.DELETE_ENTITY: GraphAction.DELETE_ENTITY,
        GraphAction.REMOVE_DELETED_ENTITY: GraphAction.REMOVE_DELETED_ENTITY
    }

    def __init__(self, transformers):
        super(ConsistencyTransformer, self).__init__(transformers)

    def _create_snapshot_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    @staticmethod
    def _create_vertex(entity_event):
        metadata = {
            VProps.IS_REAL_VITRAGE_ID:
                entity_event.get(VProps.IS_REAL_VITRAGE_ID, False)
        }

        return graph_utils.create_vertex(
            entity_event[VProps.VITRAGE_ID],
            vitrage_sample_timestamp=entity_event[DSProps.SAMPLE_DATE],
            metadata=metadata
        )

    def _create_entity_key(self, entity_event):
        return None

    def _create_snapshot_neighbors(self, entity_event):
        return None

    def _create_update_neighbors(self, entity_event):
        return None

    def get_vitrage_type(self):
        return CONSISTENCY_DATASOURCE
