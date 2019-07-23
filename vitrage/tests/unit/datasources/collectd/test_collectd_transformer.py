# Copyright 2017 - Nokia
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

import time

from oslo_config import cfg

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import UpdateMethod
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.collectd import COLLECTD_DATASOURCE
from vitrage.datasources.collectd.properties import \
    CollectdProperties as CProps
from vitrage.datasources.collectd.transformer import CollectdTransformer
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.host.transformer import HostTransformer
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests.mocks import mock_transformer
from vitrage.tests.unit.datasources.test_alarm_transformer_base import \
    BaseAlarmTransformerTest
from vitrage.utils.datetime import format_unix_timestamp


# noinspection PyProtectedMember
class TestCollectdTransformer(BaseAlarmTransformerTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH),
    ]

    def setUp(self):
        super(TestCollectdTransformer, self).setUp()
        self.transformers = {}
        self.transformers[COLLECTD_DATASOURCE] = \
            CollectdTransformer(self.transformers)
        self.transformers[NOVA_HOST_DATASOURCE] = \
            HostTransformer(self.transformers)

    def test_create_update_entity_vertex(self):
        # Test setup
        time1 = time.time()
        host1 = 'compute-1'
        event = self._generate_event(time1, host1, 'WARNING')
        self.assertIsNotNone(event)

        # Test action
        transformer = self.transformers[COLLECTD_DATASOURCE]
        wrapper = transformer.transform(event)

        # Test assertions
        self._validate_vertex_props(wrapper.vertex, event)

        entity_key = transformer._create_entity_key(event)
        entity_uuid = TransformerBase.uuid_from_deprecated_vitrage_id(
            entity_key)

        # Validate the neighbors: only one valid host neighbor
        self._validate_host_neighbor(wrapper, entity_uuid, host1)

        # Validate the expected action on the graph - update or delete
        self._validate_graph_action(wrapper)

        # Create an event with status 'UP'
        time2 = time.time()
        host2 = 'compute-2'
        event = self._generate_event(time2, host2, 'OK')
        self.assertIsNotNone(event)

        # Test action
        entity_key = transformer._create_entity_key(event)
        entity_uuid = \
            TransformerBase.uuid_from_deprecated_vitrage_id(entity_key)

        transformer = self.transformers[COLLECTD_DATASOURCE]
        wrapper = transformer.transform(event)

        # Test assertions
        self._validate_vertex_props(wrapper.vertex, event)
        self._validate_host_neighbor(wrapper, entity_uuid, host2)
        self._validate_graph_action(wrapper)

    def _validate_vertex_props(self, vertex, event):
        timestamp = format_unix_timestamp(event[CProps.TIME])
        self._validate_alarm_vertex_props(vertex,
                                          event[CProps.MESSAGE],
                                          COLLECTD_DATASOURCE,
                                          timestamp)

    @staticmethod
    def _generate_event(time, hostname, severity):
        # fake query result to be used by the transformer for determining
        # the neighbor
        query_result = [{VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE,
                         VProps.ID: hostname}]

        update_vals = {CProps.HOST: hostname,
                       CProps.SEVERITY: severity,
                       CProps.TIME: time,
                       DSProps.SAMPLE_DATE: format_unix_timestamp(time),
                       CProps.RESOURCE_NAME: hostname,
                       TransformerBase.QUERY_RESULT: query_result}

        generators = mock_transformer.simple_collectd_alarm_generators(
            update_vals=update_vals)

        return mock_transformer.generate_random_events_list(generators)[0]

    def _is_erroneous(self, vertex):
        return vertex[CProps.SEVERITY] != 'OK'
