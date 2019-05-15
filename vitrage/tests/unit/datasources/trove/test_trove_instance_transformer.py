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

import datetime

from oslo_config import cfg
from oslo_log import log as logging
from testtools import matchers

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import UpdateMethod
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import transformer_base as tb
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.datasources.trove.instance.transformer import \
    TroveInstanceTransformer
from vitrage.datasources.trove.instance import TROVE_INSTANCE_DATASOURCE
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver as mock_sync

LOG = logging.getLogger(__name__)


class TroveInstanceTransformerTest(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD, default=UpdateMethod.PULL),
    ]

    @classmethod
    def setUpClass(cls):
        super(TroveInstanceTransformerTest, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=TROVE_INSTANCE_DATASOURCE)
        cls.transformers[TROVE_INSTANCE_DATASOURCE] = \
            TroveInstanceTransformer(cls.transformers)

    def test_create_placeholder_vertex(self):
        # Tests setup
        instance_id = 'tr-instance-0'
        timestamp = datetime.datetime.utcnow()

        properties = {
            VProps.ID: instance_id,
            VProps.VITRAGE_TYPE: TROVE_INSTANCE_DATASOURCE,
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_SAMPLE_TIMESTAMP: timestamp
        }

        transformer = self.transformers[TROVE_INSTANCE_DATASOURCE]

        # Test action
        placeholder = transformer.create_neighbor_placeholder_vertex(
            **properties)

        # Test assertions
        expected_key = tb.build_key(
            transformer._key_values(TROVE_INSTANCE_DATASOURCE, instance_id))
        expected_uuid = TransformerBase.uuid_from_deprecated_vitrage_id(
            expected_key)
        self.assertEqual(expected_uuid, placeholder.vertex_id)

        self.assertEqual(timestamp,
                         placeholder.get(VProps.VITRAGE_SAMPLE_TIMESTAMP))

        self.assertEqual(TROVE_INSTANCE_DATASOURCE,
                         placeholder.get(VProps.VITRAGE_TYPE))

        self.assertEqual(instance_id, placeholder.get(VProps.ID))

        self.assertEqual(EntityCategory.RESOURCE,
                         placeholder.get(VProps.VITRAGE_CATEGORY))

        self.assertTrue(placeholder.get(VProps.VITRAGE_IS_PLACEHOLDER))

    def test_snapshot_event_transform(self):
        # Test setup
        spec_list = mock_sync.simple_trove_instance_generators(
            inst_num=1, snapshot_events=10)
        events = mock_sync.generate_random_events_list(spec_list)

        for event in events:
            # Test action
            transformer = self.transformers[TROVE_INSTANCE_DATASOURCE]
            wrapper = transformer.transform(event)

            # Test assertions
            vertex = wrapper.vertex
            self._validate_vertex_props(vertex, event)

            neighbours = wrapper.neighbors
            self.assertThat(neighbours, matchers.HasLength(1))
            self._validate_server_neighbour(neighbours[0], vertex.vertex_id,
                                            event)

    def _validate_vertex_props(self, vertex, event):
        self.assertEqual(event['id'], vertex[VProps.ID])

        self.assertEqual(event['name'], vertex[VProps.NAME])

        self.assertEqual(event['status'], vertex[VProps.STATE])

        self.assertEqual(event['tenant_id'], vertex[VProps.PROJECT_ID])

        self.assertEqual(event[DSProps.SAMPLE_DATE],
                         vertex[VProps.VITRAGE_SAMPLE_TIMESTAMP])

        self.assertEqual(EntityCategory.RESOURCE,
                         vertex[VProps.VITRAGE_CATEGORY])

        self.assertEqual(TROVE_INSTANCE_DATASOURCE,
                         vertex[VProps.VITRAGE_TYPE])

        self.assertFalse(vertex[VProps.VITRAGE_IS_PLACEHOLDER])
        self.assertFalse(vertex[VProps.VITRAGE_IS_DELETED])

    def _validate_server_neighbour(self, neighbour, instance_id, event):
        vertex, edge = neighbour.vertex, neighbour.edge

        # Validate neighbor vertex
        self.assertEqual(EntityCategory.RESOURCE,
                         vertex[VProps.VITRAGE_CATEGORY])

        self.assertEqual(NOVA_INSTANCE_DATASOURCE, vertex[VProps.VITRAGE_TYPE])

        self.assertEqual(event['server_id'], vertex[VProps.ID])

        self.assertTrue(vertex[VProps.VITRAGE_IS_PLACEHOLDER])
        self.assertFalse(vertex[VProps.VITRAGE_IS_DELETED])

        # Validate neighbor edge
        self.assertEqual(edge.target_id, vertex.vertex_id)
        self.assertEqual(edge.source_id, instance_id)
        self.assertEqual(edge.label, EdgeLabel.CONTAINS)
