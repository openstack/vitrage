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

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import EventProperties as EventProps
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.alarm_transformer_base import AlarmTransformerBase
from vitrage.datasources.doctor import DOCTOR_DATASOURCE
from vitrage.datasources.doctor.properties import DoctorDetails
from vitrage.datasources.doctor.properties import DoctorProperties \
    as DoctorProps
from vitrage.datasources.doctor.properties import DoctorStatus
from vitrage.datasources.doctor.properties import get_detail
from vitrage.datasources import transformer_base as tbase
import vitrage.graph.utils as graph_utils
from vitrage.utils.datetime import change_time_str_format

LOG = logging.getLogger(__name__)


class DoctorTransformer(AlarmTransformerBase):

    def _create_snapshot_entity_vertex(self, entity_event):
        # The Doctor monitor does not support snapshot mode
        return None

    def _create_update_entity_vertex(self, entity_event):
        self._unify_time_format(entity_event)

        details = entity_event.get(EventProps.DETAILS, {})
        details[VProps.NAME] = entity_event[EventProps.TYPE]
        details[EventProps.TIME] = entity_event[EventProps.TIME]
        if DoctorDetails.SEVERITY not in details:
            LOG.debug('adding default severity - CRITICAL')
            details[DoctorDetails.SEVERITY] = 'critical'

        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.ALARM,
            vitrage_type=entity_event[DSProps.ENTITY_TYPE],
            vitrage_sample_timestamp=entity_event[DSProps.SAMPLE_DATE],
            entity_state=self._get_alarm_state(entity_event),
            update_timestamp=entity_event[DoctorProps.UPDATE_TIME],
            metadata=details)

    def _create_update_neighbors(self, entity_event):
        return [self._create_neighbor(
            entity_event,
            get_detail(entity_event, DoctorDetails.HOSTNAME),
            DoctorProps.HOST_TYPE,
            EdgeLabel.ON,
            neighbor_category=EntityCategory.RESOURCE)]

    def _create_entity_key(self, entity_event):
        return tbase.build_key((
            EntityCategory.ALARM,
            entity_event[DSProps.ENTITY_TYPE],
            entity_event[EventProps.TYPE],
            get_detail(entity_event, DoctorDetails.HOSTNAME)))

    def get_vitrage_type(self):
        return DOCTOR_DATASOURCE

    def _ok_status(self, entity_event):
        return entity_event and \
            get_detail(entity_event, DoctorDetails.STATUS) == DoctorStatus.UP

    @staticmethod
    def get_enrich_query(event):
        hostname = get_detail(event, DoctorDetails.HOSTNAME)
        if not hostname:
            return None
        return {VProps.ID: hostname}

    @staticmethod
    def _unify_time_format(entity_event):
        DoctorTransformer._unify_prop_time_format(entity_event,
                                                  EventProps.TIME)
        DoctorTransformer._unify_prop_time_format(entity_event,
                                                  DoctorProps.UPDATE_TIME)

    @staticmethod
    def _unify_prop_time_format(entity_event, prop):
        entity_event[prop] = change_time_str_format(
            entity_event[prop],
            EventProps.TIME_FORMAT,
            tbase.TIMESTAMP_FORMAT)
