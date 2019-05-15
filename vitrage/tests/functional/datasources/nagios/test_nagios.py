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
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources.nagios.properties import NagiosTestStatus
from vitrage.datasources import NOVA_HOST_DATASOURCE
from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import NOVA_ZONE_DATASOURCE
from vitrage.tests.functional.datasources.base import \
    TestDataSourcesBase
from vitrage.tests.mocks import mock_driver


class TestNagios(TestDataSourcesBase):

    DATASOURCES_OPTS = [
        cfg.ListOpt('types',
                    default=[NAGIOS_DATASOURCE,
                             NOVA_HOST_DATASOURCE,
                             NOVA_INSTANCE_DATASOURCE,
                             NOVA_ZONE_DATASOURCE],
                    help='Names of supported driver data sources'),

        cfg.ListOpt('path',
                    default=['vitrage.datasources'],
                    help='base path for data sources')
    ]

    def setUp(self):
        super(TestNagios, self).setUp()
        self.cfg_fixture.config(group='datasources',
                                types=[
                                    NAGIOS_DATASOURCE,
                                    NOVA_HOST_DATASOURCE,
                                    NOVA_INSTANCE_DATASOURCE,
                                    NOVA_ZONE_DATASOURCE
                                ])
        self.load_datasources()

    def test_nagios_validity(self):
        # Setup
        processor = self._create_processor_with_graph()
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices())
                        )

        spec_list = mock_driver.simple_nagios_alarm_generators(
            host_num=1,
            events_num=1)
        static_events = mock_driver.generate_random_events_list(spec_list)
        nagios_event = static_events[0]
        nagios_event['resource_name'] = \
            self._find_entity_id_by_type(processor.entity_graph,
                                         NOVA_HOST_DATASOURCE)
        nagios_event['status'] = NagiosTestStatus.CRITICAL

        # Action
        processor.process_event(nagios_event)

        # Test assertions
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices() + 1)
                        )

        nagios_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE
            })
        self.assertThat(nagios_vertices, matchers.HasLength(1))

        nagios_neighbors = processor.entity_graph.neighbors(
            nagios_vertices[0].vertex_id)
        self.assertThat(nagios_neighbors, matchers.HasLength(1))

        self.assertEqual(NOVA_HOST_DATASOURCE,
                         nagios_neighbors[0][VProps.VITRAGE_TYPE])
