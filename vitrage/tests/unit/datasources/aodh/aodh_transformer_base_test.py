# Copyright 2016 - ZTE, Nokia
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
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.alarm_properties import AlarmProperties as AlarmProps
from vitrage.datasources.aodh.properties import AodhProperties as AodhProps
from vitrage.datasources.aodh.properties import AodhState
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.graph.driver.elements import Vertex
from vitrage.tests import base


class AodhTransformerBaseTest(base.BaseTest):

    def _validate_aodh_vertex_props(self, vertex, event):

        self.assertEqual(EntityCategory.ALARM, vertex[VProps.VITRAGE_CATEGORY])
        self.assertEqual(event[DSProps.ENTITY_TYPE],
                         vertex[VProps.VITRAGE_TYPE])
        self.assertEqual(event[AodhProps.NAME], vertex[VProps.NAME])
        self.assertEqual(event[AodhProps.SEVERITY], vertex[VProps.SEVERITY])
        self.assertEqual(event[AodhProps.DESCRIPTION],
                         vertex[AodhProps.DESCRIPTION])
        self.assertEqual(event[AodhProps.ENABLED], vertex[AodhProps.ENABLED])
        self.assertEqual(event[AodhProps.PROJECT_ID],
                         vertex[VProps.PROJECT_ID])
        self.assertEqual(event[AodhProps.REPEAT_ACTIONS],
                         vertex[AodhProps.REPEAT_ACTIONS])
        self.assertEqual(event[AodhProps.TYPE], vertex['alarm_type'])
        if event[AodhProps.TYPE] == AodhProps.EVENT:
            self.assertEqual(event[AodhProps.EVENT_TYPE],
                             vertex[AodhProps.EVENT_TYPE])
        elif event[AodhProps.TYPE] == AodhProps.THRESHOLD:
            self.assertEqual(event[AodhProps.STATE_TIMESTAMP],
                             vertex[AodhProps.STATE_TIMESTAMP])
        self.assertEqual(event[DSProps.SAMPLE_DATE],
                         vertex[VProps.VITRAGE_SAMPLE_TIMESTAMP])

        event_status = event[AodhProps.STATE]
        if event_status == AodhState.OK:
            self.assertEqual(AlarmProps.INACTIVE_STATE,
                             vertex[VProps.STATE])
        else:
            self.assertEqual(AlarmProps.ACTIVE_STATE,
                             vertex[VProps.STATE])
        self.assertFalse(vertex[VProps.VITRAGE_IS_PLACEHOLDER])
        self.assertFalse(vertex[VProps.VITRAGE_IS_DELETED])

    def _validate_action(self, alarm, wrapper):
        if DSProps.EVENT_TYPE in alarm \
                and alarm[DSProps.EVENT_TYPE] in vars(GraphAction).values():
            self.assertEqual(alarm[DSProps.EVENT_TYPE], wrapper.action)
            return

        ds_action = alarm[DSProps.DATASOURCE_ACTION]
        if ds_action in (DatasourceAction.SNAPSHOT, DatasourceAction.UPDATE):
            self.assertEqual(GraphAction.UPDATE_ENTITY, wrapper.action)
        else:
            self.assertEqual(GraphAction.CREATE_ENTITY, wrapper.action)

    def _validate_neighbors(self, neighbors, alarm_id, event):
        resource_counter = 0

        for neighbor in neighbors:
            resource_id = event[AodhProps.RESOURCE_ID]
            self._validate_instance_neighbor(neighbor,
                                             resource_id,
                                             alarm_id)
            resource_counter += 1

        self.assertEqual(1,
                         resource_counter,
                         'Alarm can be belonged to only one resource')

    def _validate_instance_neighbor(self,
                                    alarm_neighbor,
                                    resource_id,
                                    alarm_vertex_id):
        # validate neighbor vertex
        self.assertEqual(EntityCategory.RESOURCE,
                         alarm_neighbor.vertex[VProps.VITRAGE_CATEGORY])
        self.assertEqual(NOVA_INSTANCE_DATASOURCE,
                         alarm_neighbor.vertex[VProps.VITRAGE_TYPE])
        self.assertEqual(resource_id, alarm_neighbor.vertex[VProps.ID])
        self.assertFalse(alarm_neighbor.vertex[VProps.VITRAGE_IS_PLACEHOLDER])
        self.assertFalse(alarm_neighbor.vertex[VProps.VITRAGE_IS_DELETED])

        # Validate neighbor edge
        edge = alarm_neighbor.edge
        self.assertEqual(edge.target_id, alarm_neighbor.vertex.vertex_id)
        self.assertEqual(edge.source_id, alarm_vertex_id)
        self.assertEqual(edge.label, EdgeLabel.ON)

    def _convert_dist_to_vertex(self, neighbor):
        ver_id = neighbor[VProps.VITRAGE_CATEGORY] + \
            TransformerBase.KEY_SEPARATOR + neighbor[VProps.VITRAGE_TYPE] + \
            TransformerBase.KEY_SEPARATOR + neighbor[VProps.ID]
        return Vertex(vertex_id=ver_id, properties=neighbor)
