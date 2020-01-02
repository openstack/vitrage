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

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import GraphAction
from vitrage.common.exception import VitrageTransformerError
from vitrage.datasources.alarm_properties import AlarmProperties as AlarmProps
from vitrage.datasources import transformer_base as tbase


class AlarmTransformerBase(tbase.TransformerBase):

    def _ok_status(self, entity_event):
        pass

    def _extract_graph_action(self, entity_event):

        if DSProps.EVENT_TYPE in entity_event and \
           entity_event[DSProps.EVENT_TYPE] == GraphAction.DELETE_ENTITY:
            return entity_event[DSProps.EVENT_TYPE]

        datasource_action = entity_event[DSProps.DATASOURCE_ACTION]

        if datasource_action in \
            (DatasourceAction.UPDATE, DatasourceAction.SNAPSHOT):
            return GraphAction.DELETE_ENTITY \
                if self._ok_status(entity_event) else \
                self.GRAPH_ACTION_MAPPING.get(
                    entity_event.get(DSProps.EVENT_TYPE, None),
                    GraphAction.UPDATE_ENTITY)

        if DatasourceAction.INIT_SNAPSHOT == datasource_action:
            return GraphAction.CREATE_ENTITY

        raise VitrageTransformerError('Invalid datasource action: (%s)'
                                      % datasource_action)

    def _get_alarm_state(self, entity_event):
        event_type = entity_event.get(DSProps.EVENT_TYPE, None)
        if event_type is not None:
            return AlarmProps.INACTIVE_STATE if \
                GraphAction.DELETE_ENTITY == event_type else \
                AlarmProps.ACTIVE_STATE
        else:
            return AlarmProps.INACTIVE_STATE if \
                self._ok_status(entity_event) else \
                AlarmProps.ACTIVE_STATE
