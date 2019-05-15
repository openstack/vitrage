# Copyright 2018 Samsung Electronics
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg
from testtools import matchers

from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources import NOVA_HOST_DATASOURCE
from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import NOVA_ZONE_DATASOURCE
from vitrage.datasources.trove.instance import TROVE_INSTANCE_DATASOURCE
from vitrage.tests.functional.datasources.base import TestDataSourcesBase
from vitrage.tests.mocks import mock_driver


class TestTroveInstance(TestDataSourcesBase):

    DATASOURCES_OPTS = [
        cfg.ListOpt('types',
                    default=[NAGIOS_DATASOURCE,
                             NOVA_HOST_DATASOURCE,
                             NOVA_INSTANCE_DATASOURCE,
                             NOVA_ZONE_DATASOURCE,
                             TROVE_INSTANCE_DATASOURCE],
                    help='Names of supported driver data sources'),

        cfg.ListOpt('path',
                    default=['vitrage.datasources'],
                    help='Base path for data sources')
    ]

    def setUp(self):
        super(TestTroveInstance, self).setUp()
        self.conf.register_opts(self.PROCESSOR_OPTS, group='entity_graph')
        self.conf.register_opts(self.DATASOURCES_OPTS, group='datasources')
        self.load_datasources()

    def test_trove_instance_validity(self):
        # Setup
        processor = self._create_processor_with_graph()
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices())
                        )

        spec_list = mock_driver.simple_trove_instance_generators(
            inst_num=1,
            snapshot_events=1)
        static_events = mock_driver.generate_random_events_list(spec_list)
        trove_instance_event = static_events[0]
        trove_instance_event['server_id'] = \
            self._find_entity_id_by_type(processor.entity_graph,
                                         NOVA_INSTANCE_DATASOURCE)

        # Action
        processor.process_event(trove_instance_event)

        # Test assertions
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices() + 1)
                        )

        trove_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                VProps.VITRAGE_TYPE: TROVE_INSTANCE_DATASOURCE
            })
        self.assertThat(trove_vertices, matchers.HasLength(1))

        trove_neighbors = processor.entity_graph.neighbors(
            trove_vertices[0].vertex_id)
        self.assertThat(trove_neighbors, matchers.HasLength(1))
        self.assertEqual(NOVA_INSTANCE_DATASOURCE,
                         trove_neighbors[0][VProps.VITRAGE_TYPE])
