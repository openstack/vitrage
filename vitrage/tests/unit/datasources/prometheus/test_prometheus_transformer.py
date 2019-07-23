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
import uuid

from oslo_config import cfg

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import UpdateMethod
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.host.transformer import HostTransformer
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.nova.instance.transformer import InstanceTransformer
from vitrage.datasources.prometheus import PROMETHEUS_DATASOURCE
from vitrage.datasources.prometheus.properties import get_label
from vitrage.datasources.prometheus.properties import PrometheusAlertLabels \
    as PLabels
from vitrage.datasources.prometheus.properties import \
    PrometheusAlertProperties as PProps
from vitrage.datasources.prometheus.properties import PrometheusAlertStatus \
    as PAlertStatus
from vitrage.datasources.prometheus.transformer import PrometheusTransformer
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests.mocks import mock_transformer
from vitrage.tests.unit.datasources.test_alarm_transformer_base import \
    BaseAlarmTransformerTest


# noinspection PyProtectedMember
class PrometheusTransformerTest(BaseAlarmTransformerTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH),
    ]

    def setUp(self):
        super(PrometheusTransformerTest, self).setUp()
        self.transformers = {}
        self.conf_reregister_opts(self.OPTS, group=PROMETHEUS_DATASOURCE)
        self.transformers[NOVA_HOST_DATASOURCE] = \
            HostTransformer(self.transformers)
        self.transformers[NOVA_INSTANCE_DATASOURCE] = \
            InstanceTransformer(self.transformers)
        self.transformers[PROMETHEUS_DATASOURCE] = \
            PrometheusTransformer(self.transformers)

    def test_create_update_entity_vertex(self):
        # Test setup
        host1 = 'host1'
        instance_id = uuid.uuid4().hex
        event_on_host = self._generate_event_on_host(host1)
        event_on_instance = self._generate_event_on_instance(host1,
                                                             instance_id)
        self.assertIsNotNone(event_on_host)
        self.assertIsNotNone(event_on_instance)

        # Test action
        transformer = self.transformers[PROMETHEUS_DATASOURCE]
        wrapper_for_host = transformer.transform(event_on_host)
        wrapper_for_instance = transformer.transform(event_on_instance)

        # Test assertions
        self._validate_vertex_props(wrapper_for_host.vertex, event_on_host)
        self._validate_vertex_props(wrapper_for_instance.vertex,
                                    event_on_instance)

        # Validate the neighbors: only one valid host neighbor
        host_entity_key = transformer._create_entity_key(event_on_host)
        host_entity_uuid = \
            transformer.uuid_from_deprecated_vitrage_id(host_entity_key)

        instance_entity_key = transformer._create_entity_key(event_on_instance)
        instance_entity_uuid = \
            transformer.uuid_from_deprecated_vitrage_id(instance_entity_key)

        self._validate_host_neighbor(wrapper_for_host,
                                     host_entity_uuid,
                                     host1)

        self._validate_instance_neighbor(wrapper_for_instance,
                                         instance_entity_uuid,
                                         instance_id)

        # Validate the expected action on the graph - update or delete
        self._validate_graph_action(wrapper_for_host)
        self._validate_graph_action(wrapper_for_instance)

    def _validate_vertex_props(self, vertex, event):
        self._validate_alarm_vertex_props(
            vertex, get_label(event, PLabels.ALERT_NAME),
            PROMETHEUS_DATASOURCE, event[DSProps.SAMPLE_DATE])

    def _generate_event_on_host(self, hostname):
        # fake query result to be used by the transformer for determining
        # the neighbor
        query_result = [{VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE,
                         VProps.ID: hostname}]
        labels = {PLabels.SEVERITY: 'critical',
                  PLabels.INSTANCE: hostname}

        update_vals = {TransformerBase.QUERY_RESULT: query_result,
                       PProps.LABELS: labels}
        return self._generate_event(update_vals)

    def _generate_event_on_instance(self, hostname, instance_name):
        # fake query result to be used by the transformer for determining
        # the neighbor
        query_result = [{VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE,
                         VProps.ID: instance_name}]
        labels = {PLabels.SEVERITY: 'critical',
                  PLabels.INSTANCE: hostname,
                  PLabels.DOMAIN: instance_name}

        update_vals = {TransformerBase.QUERY_RESULT: query_result,
                       PProps.LABELS: labels}
        return self._generate_event(update_vals)

    @staticmethod
    def _generate_event(update_vals):
        generators = mock_transformer.simple_prometheus_alarm_generators(
            update_vals=update_vals)

        return mock_transformer.generate_random_events_list(generators)[0]

    def _is_erroneous(self, vertex):
        return vertex[PProps.STATUS] == PAlertStatus.FIRING
