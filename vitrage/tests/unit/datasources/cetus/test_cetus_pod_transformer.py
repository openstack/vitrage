# Copyright 2020 - Inspur - Qitao
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

import datetime

from oslo_config import cfg
from oslo_log import log as logging

from testtools import matchers

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import UpdateMethod
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.cetus.pod import CETUS_POD_DATASOURCE
from vitrage.datasources.cetus.pod.transformer import PodTransformer
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests import base

from vitrage.utils.datetime import format_utcnow

LOG = logging.getLogger(__name__)

events = [
    {
        'name': 'app01-3232323232',
        'id': '0903912039123',
        'status': 'Pending',
        'node': 'd7f8b66d-5221-4b4c-ade8-416a6a7bc661'
    }, {
        'name': 'app02-3232323232',
        'id': '0903912039122',
        'status': 'Pending',
        'node': '85ac015b-ec84-4d3c-a56e-d97fafff6a2a'
    }]


class TestCetusClusterTransformer(base.BaseTest):
    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PULL),
    ]

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(TestCetusClusterTransformer, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=CETUS_POD_DATASOURCE)
        cls.transformers[CETUS_POD_DATASOURCE] = PodTransformer(
            cls.transformers)

    def test_create_placeholder_vertex(self):
        LOG.debug('Cetus pod transformer test: Test create placeholder '
                  'vertex')

        # Test setup
        pod_id = "pod123"
        timestamp = datetime.datetime.utcnow()
        pod_transformer = self.transformers[CETUS_POD_DATASOURCE]

        # Test action
        properties = {
            VProps.ID: pod_id,
            VProps.VITRAGE_TYPE: CETUS_POD_DATASOURCE,
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_SAMPLE_TIMESTAMP: timestamp
        }
        placeholder = \
            pod_transformer.create_neighbor_placeholder_vertex(**properties)

        # Test assertions
        observed_uuid = placeholder.vertex_id
        expected_key = tbase.build_key(pod_transformer._key_values(
            CETUS_POD_DATASOURCE,
            pod_id))
        expected_uuid = \
            TransformerBase.uuid_from_deprecated_vitrage_id(expected_key)
        self.assertEqual(expected_uuid, observed_uuid)

        observed_time = placeholder.get(VProps.VITRAGE_SAMPLE_TIMESTAMP)
        self.assertEqual(timestamp, observed_time)

        observed_subtype = placeholder.get(VProps.VITRAGE_TYPE)
        self.assertEqual(CETUS_POD_DATASOURCE, observed_subtype)

        observed_entity_id = placeholder.get(VProps.ID)
        self.assertEqual(pod_id, observed_entity_id)

        observed_vitrage_category = placeholder.get(VProps.VITRAGE_CATEGORY)
        self.assertEqual(EntityCategory.RESOURCE, observed_vitrage_category)

        vitrage_is_placeholder = placeholder.get(
            VProps.VITRAGE_IS_PLACEHOLDER)
        self.assertTrue(vitrage_is_placeholder)

    def test_key_values(self):

        LOG.debug('Test key values')

        # Test setup
        pod_id = "pod123456"
        pod_transformer = self.transformers[CETUS_POD_DATASOURCE]
        # Test action
        observed_key_fields = pod_transformer._key_values(
            CETUS_POD_DATASOURCE,
            pod_id)

        # Test assertions
        self.assertEqual(EntityCategory.RESOURCE, observed_key_fields[0])
        self.assertEqual(CETUS_POD_DATASOURCE, observed_key_fields[1])
        self.assertEqual(pod_id, observed_key_fields[2])

    def test_snapshot_event_transform(self):
        sample_timestamp = format_utcnow()
        for event in events:
            event[DSProps.DATASOURCE_ACTION] = DatasourceAction.SNAPSHOT
            event[DSProps.SAMPLE_DATE] = sample_timestamp
            wrapper = self.transformers[CETUS_POD_DATASOURCE].transform(event)
            vertex = wrapper.vertex
            self._validate_vertex_props(vertex, event)
            neighbors = wrapper.neighbors
            self.assertThat(neighbors, matchers.HasLength(1))
            self._validate_neighbors(neighbors, vertex.vertex_id)

    def _validate_neighbors(self, neighbors, instance_vertex_id):
        node_neighbors_counter = 0
        for neighbor in neighbors:
            node_neighbors_counter += 1
            self._validate_node_neighbor(neighbor, instance_vertex_id)

        self.assertEqual(1, node_neighbors_counter)

    def _validate_node_neighbor(self, node_neighbor, instance_vertex_id):

        self.assertEqual(node_neighbor.vertex[VProps.VITRAGE_ID],
                         node_neighbor.vertex.vertex_id)
        self.assertFalse(node_neighbor.vertex[VProps.VITRAGE_IS_DELETED])

        self.assertTrue(node_neighbor.vertex[VProps.VITRAGE_IS_PLACEHOLDER])
        self.assertEqual(NOVA_INSTANCE_DATASOURCE,
                         node_neighbor.vertex[VProps.VITRAGE_TYPE])

        # Validate neighbor edge
        edge = node_neighbor.edge
        self.assertEqual(edge.source_id, node_neighbor.vertex.vertex_id)
        self.assertEqual(edge.target_id, instance_vertex_id)

    def _validate_vertex_props(self, vertex, event):

        extract_value = tbase.extract_field_value

        expected_id = extract_value(event, 'id')
        observed_id = vertex[VProps.ID]
        self.assertEqual(expected_id, observed_id)

        self.assertEqual(EntityCategory.RESOURCE,
                         vertex[VProps.VITRAGE_CATEGORY])

        self.assertEqual(CETUS_POD_DATASOURCE,
                         vertex[VProps.VITRAGE_TYPE])

        expected_timestamp = event[DSProps.SAMPLE_DATE]
        observed_timestamp = vertex[VProps.VITRAGE_SAMPLE_TIMESTAMP]
        self.assertEqual(expected_timestamp, observed_timestamp)

        expected_name = extract_value(event, 'name')
        observed_name = vertex[VProps.NAME]
        self.assertEqual(expected_name, observed_name)

        vitrage_is_placeholder = vertex[VProps.VITRAGE_IS_PLACEHOLDER]
        self.assertFalse(vitrage_is_placeholder)

        vitrage_is_deleted = vertex[VProps.VITRAGE_IS_DELETED]
        self.assertFalse(vitrage_is_deleted)
