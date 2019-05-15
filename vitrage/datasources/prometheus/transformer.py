# Copyright 2018 - Nokia
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
from vitrage.common.constants import EntityCategory as ECategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.alarm_transformer_base import AlarmTransformerBase
from vitrage.datasources.prometheus import PROMETHEUS_DATASOURCE
from vitrage.datasources.prometheus.properties import get_alarm_update_time
from vitrage.datasources.prometheus.properties import get_label
from vitrage.datasources.prometheus.properties import PrometheusAlertLabels \
    as PAlertLabels
from vitrage.datasources.prometheus.properties \
    import PrometheusAlertProperties as PProps
from vitrage.datasources.prometheus.properties import PrometheusAlertStatus \
    as PAlertStatus
from vitrage.datasources.prometheus.properties \
    import PrometheusDatasourceProperties as PDProps
from vitrage.datasources import transformer_base as tbase
import vitrage.graph.utils as graph_utils

LOG = logging.getLogger(__name__)


class PrometheusTransformer(AlarmTransformerBase):

    def _create_snapshot_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_vertex(self, entity_event):
        metadata = {
            VProps.NAME: get_label(entity_event, PAlertLabels.ALERT_NAME),
            VProps.SEVERITY: get_label(entity_event, PAlertLabels.SEVERITY),
            PProps.STATUS: entity_event.get(PProps.STATUS),
        }
        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=ECategory.ALARM,
            vitrage_type=entity_event[DSProps.ENTITY_TYPE],
            vitrage_sample_timestamp=entity_event[DSProps.SAMPLE_DATE],
            entity_state=self._get_alarm_state(entity_event),
            update_timestamp=get_alarm_update_time(entity_event),
            metadata=metadata
        )

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_prometheus_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_prometheus_neighbors(entity_event)

    def _create_prometheus_neighbors(self, entity_event):
        graph_neighbors = entity_event.get(self.QUERY_RESULT, [])
        return [self._create_neighbor(entity_event,
                                      graph_neighbor[VProps.ID],
                                      graph_neighbor[VProps.VITRAGE_TYPE],
                                      EdgeLabel.ON,
                                      neighbor_category=ECategory.RESOURCE)
                for graph_neighbor in graph_neighbors]

    def _create_entity_key(self, entity_event):
        return tbase.build_key((ECategory.ALARM,
                                entity_event[DSProps.ENTITY_TYPE],
                                get_label(entity_event,
                                          PAlertLabels.ALERT_NAME),
                                str(entity_event.get(
                                    PDProps.ENTITY_UNIQUE_PROPS))))

    def get_vitrage_type(self):
        return PROMETHEUS_DATASOURCE

    def _ok_status(self, entity_event):
        return entity_event and \
            PAlertStatus.RESOLVED == entity_event.get(PProps.STATUS)

    @staticmethod
    def get_enrich_query(event):
        LOG.debug('event for enrich query: %s', event)
        entity_unique_props = event.get(PDProps.ENTITY_UNIQUE_PROPS)
        return entity_unique_props
