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
from testtools import matchers

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.collectd import COLLECTD_DATASOURCE
from vitrage.datasources.collectd.properties import \
    CollectdProperties as CProps
from vitrage.datasources import NOVA_HOST_DATASOURCE
from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import NOVA_ZONE_DATASOURCE
from vitrage.tests.functional.datasources.base import \
    TestDataSourcesBase
from vitrage.tests.mocks import mock_transformer
from vitrage.utils.datetime import format_unix_timestamp


class TestCollectd(TestDataSourcesBase):

    DATASOURCES_OPTS = [
        cfg.ListOpt('types',
                    default=[COLLECTD_DATASOURCE,
                             NOVA_HOST_DATASOURCE,
                             NOVA_INSTANCE_DATASOURCE,
                             NOVA_ZONE_DATASOURCE],
                    help='Names of supported driver data sources'),

        cfg.ListOpt('path',
                    default=['vitrage.datasources'],
                    help='base path for data sources')
    ]

    def setUp(self):
        super(TestCollectd, self).setUp()
        self.cfg_fixture.config(group='datasources',
                                types=[
                                    COLLECTD_DATASOURCE,
                                    NOVA_HOST_DATASOURCE,
                                    NOVA_INSTANCE_DATASOURCE,
                                    NOVA_ZONE_DATASOURCE
                                ])
        self.load_datasources()

    def test_collectd_alarm_on_host(self):
        self._test_collectd_alarm(NOVA_HOST_DATASOURCE, 'host-2', 'host-2')

    def test_collectd_alarm_on_instance(self):
        self._test_collectd_alarm(NOVA_INSTANCE_DATASOURCE, 'vm-5', 'host-4')

    def _test_collectd_alarm(self, resource_type, resource_name, host_name):
        # Setup
        processor = self._create_processor_with_graph()
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices())
                        )

        time1 = time.time()
        severity1 = 'WARNING'
        link_down_message = 'link state of "qvo818dd156-be" is "DOWN"'
        collectd_event = self._create_collectd_event(time1,
                                                     resource_type,
                                                     resource_name,
                                                     host_name,
                                                     severity1,
                                                     link_down_message)

        # Action
        processor.process_event(collectd_event)

        # Test assertions
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices() + 1)
                        )

        collectd_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                VProps.VITRAGE_TYPE: COLLECTD_DATASOURCE
            })

        self.assertThat(collectd_vertices, matchers.HasLength(1))
        collectd_vertex1 = collectd_vertices[0]
        self._assert_collectd_vertex_equals(collectd_vertex1,
                                            time1,
                                            resource_type,
                                            resource_name,
                                            severity1)

        collectd_neighbors = processor.entity_graph.neighbors(
            collectd_vertices[0].vertex_id)

        self._assert_collectd_neighbor_equals(collectd_neighbors,
                                              resource_type,
                                              resource_name)

        # Action 2 - update the existing alarm
        time2 = time.time()
        severity2 = 'ERROR'
        collectd_event = self._create_collectd_event(time2,
                                                     resource_type,
                                                     resource_name,
                                                     host_name,
                                                     severity2,
                                                     link_down_message)

        processor.process_event(collectd_event)

        # Test assertions - the collectd alarm vertex should be the same
        self.assertThat(processor.entity_graph,
                        matchers.HasLength(
                            self._num_total_expected_vertices() + 1)
                        )

        collectd_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                VProps.VITRAGE_TYPE: COLLECTD_DATASOURCE
            })

        self.assertThat(collectd_vertices, matchers.HasLength(1))
        collectd_vertex2 = collectd_vertices[0]
        self.assertEqual(collectd_vertex1[VProps.VITRAGE_ID],
                         collectd_vertex2[VProps.VITRAGE_ID])

        # Action 3 - clear the alarm
        time3 = time.time()
        severity3 = 'OK'
        link_up_message = 'link state of "qvo818dd156-be" is "UP"'
        collectd_event = self._create_collectd_event(time3,
                                                     resource_type,
                                                     resource_name,
                                                     host_name,
                                                     severity3,
                                                     link_up_message)

        processor.process_event(collectd_event)

        # Test assertions - the collectd alarm vertex should be removed
        collectd_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter={
                VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                VProps.VITRAGE_TYPE: COLLECTD_DATASOURCE
            })

        self._assert_no_vertex(collectd_vertices)

    @staticmethod
    def _create_collectd_event(time,
                               resource_type,
                               resource_name,
                               host_name,
                               severity,
                               message):
        update_vals = {CProps.TIME: time,
                       DSProps.SAMPLE_DATE: format_unix_timestamp(time),
                       CProps.HOST: host_name,
                       CProps.RESOURCE_TYPE: resource_type,
                       CProps.RESOURCE_NAME: resource_name,
                       CProps.MESSAGE: message,
                       CProps.SEVERITY: severity}

        spec_list = mock_transformer.simple_collectd_alarm_generators(
            update_vals=update_vals)
        static_events = mock_transformer.generate_random_events_list(spec_list)

        return static_events[0]

    def _assert_collectd_vertex_equals(self,
                                       collectd_vertex,
                                       expected_time,
                                       expected_resource_type,
                                       expected_resource_name,
                                       expected_severity):

        self.assertEqual(format_unix_timestamp(expected_time),
                         collectd_vertex[VProps.VITRAGE_SAMPLE_TIMESTAMP])
        self.assertEqual(expected_resource_type,
                         collectd_vertex[VProps.VITRAGE_RESOURCE_TYPE])
        self.assertEqual(expected_resource_name,
                         collectd_vertex[CProps.RESOURCE_NAME])
        self.assertEqual(expected_severity, collectd_vertex[VProps.SEVERITY])

    def _assert_collectd_neighbor_equals(self,
                                         collectd_neighbors,
                                         expected_resource_type,
                                         expected_resource_name):
        self.assertThat(collectd_neighbors, matchers.HasLength(1))

        self.assertEqual(expected_resource_type,
                         collectd_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual(expected_resource_name,
                         collectd_neighbors[0][VProps.NAME])

    def _assert_no_vertex(self, vertices):
        self.assertTrue(len(vertices) == 0 or
                        (len(vertices) == 1 and
                         vertices[0].get(VProps.VITRAGE_IS_DELETED, False)))
