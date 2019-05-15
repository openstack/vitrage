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

from oslo_config import cfg
from testtools import matchers

from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources import CINDER_VOLUME_DATASOURCE
from vitrage.datasources.heat.stack import HEAT_STACK_DATASOURCE
from vitrage.datasources import NOVA_HOST_DATASOURCE
from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import NOVA_ZONE_DATASOURCE
from vitrage.tests.functional.datasources.base import TestDataSourcesBase
from vitrage.tests.mocks import mock_driver


class TestHeatStack(TestDataSourcesBase):

    DATASOURCES_OPTS = [
        cfg.ListOpt('types',
                    default=[HEAT_STACK_DATASOURCE,
                             NOVA_HOST_DATASOURCE,
                             NOVA_INSTANCE_DATASOURCE,
                             NOVA_ZONE_DATASOURCE,
                             CINDER_VOLUME_DATASOURCE],
                    help='Names of supported driver data sources'),

        cfg.ListOpt('path',
                    default=['vitrage.datasources'],
                    help='base path for data sources')
    ]

    def setUp(self):
        super(TestHeatStack, self).setUp()
        self.cfg_fixture.config(group='datasources',
                                types=[
                                    HEAT_STACK_DATASOURCE,
                                    NOVA_HOST_DATASOURCE,
                                    NOVA_INSTANCE_DATASOURCE,
                                    NOVA_ZONE_DATASOURCE,
                                    CINDER_VOLUME_DATASOURCE])
        self.load_datasources()

    def test_heat_stack_validity(self):
        # Setup
        processor = self._create_processor_with_graph()
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices())
                        )

        spec_list = mock_driver.simple_stack_generators(
            stack_num=1,
            instance_and_volume_num=1,
            snapshot_events=1)
        static_events = mock_driver.generate_random_events_list(spec_list)
        heat_stack_event = static_events[0]

        # Action
        processor.process_event(heat_stack_event)

        # Test assertions
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices() + 3)
                        )

        stack_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                VProps.VITRAGE_TYPE: HEAT_STACK_DATASOURCE
            })
        self.assertThat(stack_vertices, matchers.HasLength(1))

        instance_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE
            })
        self.assertThat(instance_vertices,
                        matchers.HasLength(self.NUM_INSTANCES + 1))

        cinder_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                VProps.VITRAGE_TYPE: CINDER_VOLUME_DATASOURCE
            })
        self.assertThat(cinder_vertices, matchers.HasLength(1))

        stack_neighbors = processor.entity_graph.neighbors(
            stack_vertices[0].vertex_id)
        self.assertThat(stack_neighbors, matchers.HasLength(2))
