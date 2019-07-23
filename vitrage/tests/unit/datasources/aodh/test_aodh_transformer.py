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

from oslo_config import cfg
from oslo_log import log as logging
from testtools import matchers

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import UpdateMethod
from vitrage.datasources.aodh import AODH_DATASOURCE
from vitrage.datasources.aodh.properties import AodhProperties as AodhProps
from vitrage.datasources.aodh.transformer import AodhTransformer
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests.mocks import mock_transformer as mock_sync
from vitrage.tests.unit.datasources.aodh.aodh_transformer_base_test import \
    AodhTransformerBaseTest

LOG = logging.getLogger(__name__)


class TestAodhAlarmTransformer(AodhTransformerBaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PULL),
    ]

    @classmethod
    def setUpClass(cls):
        super(TestAodhAlarmTransformer, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=AODH_DATASOURCE)
        cls.transformers[AODH_DATASOURCE] = \
            AodhTransformer(cls.transformers)

    def test_key_values_with_vitrage_alarm(self):
        LOG.debug('Aodh transformer test: get key values(vitrage_alarm)')

        # Test setup
        entity = {AodhProps.VITRAGE_ID: 'test',
                  DSProps.ENTITY_TYPE: AODH_DATASOURCE,
                  AodhProps.ALARM_ID: '12345'}
        transformer = self.transformers[AODH_DATASOURCE]

        # Test action
        observed_key_fields = transformer._create_entity_key(entity)

        # Test assertions
        self.assertEqual('test', observed_key_fields)

    def test_key_values(self):
        LOG.debug('Aodh transformer test: get key values(aodh alarm)')

        # Test setup
        entity = {DSProps.ENTITY_TYPE: AODH_DATASOURCE,
                  AodhProps.ALARM_ID: '12345'}
        transformer = self.transformers[AODH_DATASOURCE]

        # Test action
        entity_key_fields = transformer._create_entity_key(entity).split(":")

        # Test assertions
        self.assertEqual(EntityCategory.ALARM, entity_key_fields[0])
        self.assertEqual(AODH_DATASOURCE, entity_key_fields[1])
        self.assertEqual(entity[AodhProps.ALARM_ID], entity_key_fields[2])

    def test_snapshot_transform(self):
        LOG.debug('Aodh alarm transformer test: transform entity event '
                  'snapshot')

        # Test setup
        spec_list = mock_sync.simple_aodh_alarm_generators(alarm_num=3,
                                                           snapshot_events=3)
        static_events = mock_sync.generate_random_events_list(spec_list)

        for event in static_events:
            # convert neighbor from dict to vertex object
            neighbors = event[TransformerBase.QUERY_RESULT]
            vertices = []
            for neighbor in neighbors:
                neighbor_vertex = self._convert_dist_to_vertex(neighbor)
                vertices.append(self.transformers[AODH_DATASOURCE].
                                update_uuid_in_vertex(neighbor_vertex))
            event[TransformerBase.QUERY_RESULT] = vertices

            # Test action
            wrapper = self.transformers[AODH_DATASOURCE].transform(event)

            # Test assertions
            vertex = wrapper.vertex
            self._validate_aodh_vertex_props(vertex, event)

            neighbors = wrapper.neighbors
            self.assertThat(neighbors, matchers.HasLength(1))
            self._validate_neighbors(neighbors, vertex.vertex_id, event)

            self._validate_action(event, wrapper)


class TestAodhAlarmPushTransformer(AodhTransformerBaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH),
    ]

    # noinspection PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(TestAodhAlarmPushTransformer, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=AODH_DATASOURCE)
        cls.transformers[AODH_DATASOURCE] = \
            AodhTransformer(cls.transformers)

    def test_update_transform(self):
        LOG.debug('Aodh update alarm transformer test:'
                  'transform entity event update')

        # Test setup
        spec_list = \
            mock_sync.simple_aodh_update_alarm_generators(alarm_num=5,
                                                          update_events=5)
        static_events = mock_sync.generate_random_events_list(spec_list)

        for event in static_events:
            # convert neighbor from dict to vertex object
            neighbors = event[TransformerBase.QUERY_RESULT]
            vertices = []
            for neighbor in neighbors:
                neighbor_vertex = self._convert_dist_to_vertex(neighbor)
                vertices.append(self.transformers[AODH_DATASOURCE].
                                update_uuid_in_vertex(neighbor_vertex))
            event[TransformerBase.QUERY_RESULT] = vertices

            # Test action
            wrapper = self.transformers[AODH_DATASOURCE].transform(event)

            # Test assertions
            vertex = wrapper.vertex
            self._validate_aodh_vertex_props(vertex, event)

            neighbors = wrapper.neighbors
            self.assertThat(neighbors, matchers.HasLength(1))
            self._validate_neighbors(neighbors, vertex.vertex_id, event)

            self._validate_action(event, wrapper)
