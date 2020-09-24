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
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import UpdateMethod
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.cetus.cluster import CETUS_CLUSTER_DATASOURCE
from vitrage.datasources.cetus.cluster.transformer import ClusterTransformer
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests import base

from vitrage.utils.datetime import format_utcnow

LOG = logging.getLogger(__name__)

events = [
    {
        'name': 'prom',
        'id': 'c-6v5gr',
        'status': 'active',
        'nodes': [
            '85ac015b-ec84-4d3c-a56e-d97fafff6a2a',
            'c241c602-8c7b-44f8-8275-50b83a42787e'
        ]
    }
]


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
        cls.conf.register_opts(cls.OPTS, group=CETUS_CLUSTER_DATASOURCE)
        cls.transformers[CETUS_CLUSTER_DATASOURCE] = ClusterTransformer(
            cls.transformers)

    def test_create_placeholder_vertex(self):
        LOG.debug('Cetus cluster transformer test: Test create placeholder '
                  'vertex')

        # Test setup
        cluster_id = "cluster123"
        timestamp = datetime.datetime.utcnow()
        cluster_transformer = self.transformers[CETUS_CLUSTER_DATASOURCE]

        # Test action
        properties = {
            VProps.ID: cluster_id,
            VProps.VITRAGE_TYPE: CETUS_CLUSTER_DATASOURCE,
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_SAMPLE_TIMESTAMP: timestamp
        }
        placeholder = \
            cluster_transformer.create_neighbor_placeholder_vertex(
                **properties)

        # Test assertions
        observed_uuid = placeholder.vertex_id
        expected_key = tbase.build_key(cluster_transformer._key_values(
            CETUS_CLUSTER_DATASOURCE,
            cluster_id))
        expected_uuid = \
            TransformerBase.uuid_from_deprecated_vitrage_id(expected_key)
        self.assertEqual(expected_uuid, observed_uuid)

        observed_time = placeholder.get(VProps.VITRAGE_SAMPLE_TIMESTAMP)
        self.assertEqual(timestamp, observed_time)

        observed_subtype = placeholder.get(VProps.VITRAGE_TYPE)
        self.assertEqual(CETUS_CLUSTER_DATASOURCE, observed_subtype)

        observed_entity_id = placeholder.get(VProps.ID)
        self.assertEqual(cluster_id, observed_entity_id)

        observed_vitrage_category = placeholder.get(VProps.VITRAGE_CATEGORY)
        self.assertEqual(EntityCategory.RESOURCE, observed_vitrage_category)

        vitrage_is_placeholder = placeholder.get(
            VProps.VITRAGE_IS_PLACEHOLDER)
        self.assertTrue(vitrage_is_placeholder)

    def test_key_values(self):

        LOG.debug('Test key values')

        # Test setup
        cluster_id = "cluster123456"
        cluster_transformer = self.transformers[CETUS_CLUSTER_DATASOURCE]
        # Test action
        observed_key_fields = cluster_transformer._key_values(
            CETUS_CLUSTER_DATASOURCE,
            cluster_id)

        # Test assertions
        self.assertEqual(EntityCategory.RESOURCE, observed_key_fields[0])
        self.assertEqual(CETUS_CLUSTER_DATASOURCE, observed_key_fields[1])
        self.assertEqual(cluster_id, observed_key_fields[2])

    def test_snapshot_event_transform(self):
        sample_timestamp = format_utcnow()
        for event in events:
            event[DSProps.DATASOURCE_ACTION] = DatasourceAction.SNAPSHOT
            event[DSProps.SAMPLE_DATE] = sample_timestamp
            wrapper = self.transformers[CETUS_CLUSTER_DATASOURCE].transform(
                event)
            vertex = wrapper.vertex

            self._validate_vertex_props(vertex, event)
            neighbors = wrapper.neighbors
            self.assertThat(neighbors, matchers.HasLength(2))
            self._validate_neighbors(neighbors, vertex.vertex_id)

    def _validate_neighbors(self, neighbors, instance_vertex_id):
        node_neighbors_counter = 0
        for neighbor in neighbors:
            self._validate_node_neighbor(neighbor,
                                         instance_vertex_id)
            node_neighbors_counter += 1

        self.assertEqual(2, node_neighbors_counter)

    def _validate_node_neighbor(self, node_neighbor, cluster_vertex_id):

        node_vertex = node_neighbor.vertex
        vitrage_type = node_vertex[VProps.VITRAGE_TYPE]
        self.assertEqual(NOVA_INSTANCE_DATASOURCE, vitrage_type)
        vitrage_is_deleted = node_vertex[VProps.VITRAGE_IS_DELETED]
        self.assertFalse(vitrage_is_deleted)
        vitrage_is_placeholder = node_vertex[VProps.VITRAGE_IS_PLACEHOLDER]
        self.assertTrue(vitrage_is_placeholder)

        # Validate neighbor edge
        edge = node_neighbor.edge
        self.assertEqual(edge.target_id, node_neighbor.vertex.vertex_id)
        self.assertEqual(edge.source_id, cluster_vertex_id)
        self.assertEqual(edge.label, EdgeLabel.CONTAINS)

    def _validate_vertex_props(self, vertex, event):

        extract_value = tbase.extract_field_value

        expected_id = extract_value(event, 'id')
        observed_id = vertex[VProps.ID]
        self.assertEqual(expected_id, observed_id)

        self.assertEqual(EntityCategory.RESOURCE,
                         vertex[VProps.VITRAGE_CATEGORY])

        self.assertEqual(CETUS_CLUSTER_DATASOURCE,
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
