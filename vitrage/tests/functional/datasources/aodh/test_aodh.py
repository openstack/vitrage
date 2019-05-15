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
from testtools import matchers

from vitrage.common.constants import DatasourceProperties as DSProp
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.aodh import AODH_DATASOURCE
from vitrage.datasources.aodh.properties import AodhProperties as AodhProps
from vitrage.datasources import NOVA_HOST_DATASOURCE
from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import NOVA_ZONE_DATASOURCE
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests.functional.datasources.base import \
    TestDataSourcesBase
from vitrage.tests.mocks import mock_transformer


class TestAodhAlarms(TestDataSourcesBase):

    DATASOURCES_OPTS = [
        cfg.ListOpt('types',
                    default=[AODH_DATASOURCE,
                             NOVA_HOST_DATASOURCE,
                             NOVA_INSTANCE_DATASOURCE,
                             NOVA_ZONE_DATASOURCE],
                    help='Names of supported driver data sources'),

        cfg.ListOpt('path',
                    default=['vitrage.datasources'],
                    help='base path for data sources')
    ]

    def setUp(self):
        super(TestAodhAlarms, self).setUp()
        self.cfg_fixture.config(group='datasources',
                                types=[
                                    AODH_DATASOURCE,
                                    NOVA_HOST_DATASOURCE,
                                    NOVA_INSTANCE_DATASOURCE,
                                    NOVA_ZONE_DATASOURCE
                                ])
        self.load_datasources()

    def test_aodh_alarms_validity(self):
        # Setup
        processor = self._create_processor_with_graph()
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices())
                        )

        detail = {TransformerBase.QUERY_RESULT: '',
                  DSProp.ENTITY_TYPE: AODH_DATASOURCE}
        spec_list = \
            mock_transformer.simple_aodh_alarm_generators(alarm_num=1,
                                                          snapshot_events=1,
                                                          snap_vals=detail)
        static_events = mock_transformer.generate_random_events_list(spec_list)

        aodh_event = static_events[0]
        aodh_event[AodhProps.RESOURCE_ID] = \
            self._find_entity_id_by_type(processor.entity_graph,
                                         NOVA_HOST_DATASOURCE)

        # Action
        processor.process_event(aodh_event)

        # Test assertions
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices() + 1)
                        )

        aodh_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                VProps.VITRAGE_TYPE: AODH_DATASOURCE
            })
        self.assertThat(aodh_vertices, matchers.HasLength(1))

        aodh_neighbors = processor.entity_graph.neighbors(
            aodh_vertices[0].vertex_id)
        self.assertThat(aodh_neighbors, matchers.HasLength(1))

        self.assertEqual(NOVA_HOST_DATASOURCE,
                         aodh_neighbors[0][VProps.VITRAGE_TYPE])
