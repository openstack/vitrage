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
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.alarm_transformer_base import AlarmTransformerBase
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources.nagios.properties import NagiosProperties
from vitrage.datasources.nagios.properties import NagiosTestStatus
from vitrage.datasources import transformer_base as tbase
import vitrage.graph.utils as graph_utils
from vitrage.utils import datetime as datetime_utils


class NagiosTransformer(AlarmTransformerBase):

    def _create_snapshot_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_vertex(self, entity_event):

        update_timestamp = datetime_utils.change_to_utc_time_and_format(
            entity_event[NagiosProperties.LAST_CHECK],
            tbase.TIMESTAMP_FORMAT)
        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]
        update_timestamp = \
            self._format_update_timestamp(update_timestamp,
                                          vitrage_sample_timestamp)

        metadata = {
            VProps.NAME: entity_event[NagiosProperties.SERVICE],
            VProps.RESOURCE_ID: entity_event[NagiosProperties.RESOURCE_NAME],
            VProps.SEVERITY: entity_event[NagiosProperties.STATUS],
            VProps.INFO: entity_event[NagiosProperties.STATUS_INFO]
        }

        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.ALARM,
            vitrage_type=entity_event[DSProps.ENTITY_TYPE],
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            entity_state=self._get_alarm_state(entity_event),
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_nagios_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_nagios_neighbors(entity_event)

    def _create_nagios_neighbors(self, entity_event):
        resource_type = entity_event[NagiosProperties.RESOURCE_TYPE]
        if resource_type:
            return [self._create_neighbor(
                entity_event,
                entity_event[NagiosProperties.RESOURCE_NAME],
                resource_type,
                EdgeLabel.ON,
                neighbor_category=EntityCategory.RESOURCE)]

        return []

    def _ok_status(self, entity_event):
        return entity_event[NagiosProperties.STATUS] == NagiosTestStatus.OK

    def _create_entity_key(self, entity_event):
        entity_type = entity_event[DSProps.ENTITY_TYPE]
        alarm_name = entity_event[NagiosProperties.SERVICE]
        resource_name = entity_event[NagiosProperties.RESOURCE_NAME]
        return tbase.build_key((EntityCategory.ALARM,
                                entity_type,
                                resource_name,
                                alarm_name))

    def get_vitrage_type(self):
        return NAGIOS_DATASOURCE
