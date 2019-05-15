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

import datetime

from oslo_config import cfg

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import UpdateMethod
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.host.transformer import HostTransformer
from vitrage.datasources.static import STATIC_DATASOURCE
from vitrage.datasources.static import StaticFields
from vitrage.datasources.static.transformer import StaticTransformer
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver


class TestStaticTransformer(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PULL),
    ]

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(TestStaticTransformer, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=STATIC_DATASOURCE)
        cls.transformer = StaticTransformer(cls.transformers)
        cls.transformers[STATIC_DATASOURCE] = cls.transformer
        cls.transformers[NOVA_HOST_DATASOURCE] = \
            HostTransformer(cls.transformers)

    # noinspection PyAttributeOutsideInit
    def setUp(self):
        super(TestStaticTransformer, self).setUp()
        self.entity_type = STATIC_DATASOURCE
        self.entity_id = '12345'
        self.timestamp = datetime.datetime.utcnow()

    def test_create_placeholder_vertex(self):
        properties = {
            VProps.VITRAGE_TYPE: self.entity_type,
            VProps.ID: self.entity_id,
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_SAMPLE_TIMESTAMP: self.timestamp
        }
        placeholder = self.transformer.create_neighbor_placeholder_vertex(
            **properties)

        observed_entity_id = placeholder.vertex_id
        expected_entity_id = \
            TransformerBase.uuid_from_deprecated_vitrage_id(
                'RESOURCE:static:12345')
        self.assertEqual(expected_entity_id, observed_entity_id)

        observed_time = placeholder.get(VProps.VITRAGE_SAMPLE_TIMESTAMP)
        self.assertEqual(self.timestamp, observed_time)

        observed_subtype = placeholder.get(VProps.VITRAGE_TYPE)
        self.assertEqual(self.entity_type, observed_subtype)

        observed_entity_id = placeholder.get(VProps.ID)
        self.assertEqual(self.entity_id, observed_entity_id)

        observed_vitrage_category = placeholder.get(VProps.VITRAGE_CATEGORY)
        self.assertEqual(EntityCategory.RESOURCE, observed_vitrage_category)

        vitrage_is_placeholder = placeholder.get(VProps.VITRAGE_IS_PLACEHOLDER)
        self.assertTrue(vitrage_is_placeholder)

    def test_snapshot_transform(self):
        vals_list = mock_driver.simple_static_generators(snapshot_events=1)
        events = mock_driver.generate_random_events_list(vals_list)
        self._event_transform_test(events)

    def test_update_transform(self):
        vals_list = mock_driver.simple_static_generators(update_events=1)
        events = mock_driver.generate_random_events_list(vals_list)
        self._event_transform_test(events)

    def _event_transform_test(self, events):
        for event in events:
            wrapper = self.transformer.transform(event)

            vertex = wrapper.vertex
            self._validate_vertex(vertex, event)

            neighbors = wrapper.neighbors
            self._validate_neighbors(neighbors, vertex.vertex_id, event)

    def _validate_vertex(self, vertex, event):
        self._validate_common_props(vertex, event)
        self.assertEqual(vertex[VProps.VITRAGE_SAMPLE_TIMESTAMP],
                         event[DSProps.SAMPLE_DATE])

        for k, v in event.get(StaticFields.METADATA, {}):
            self.assertEqual(v, vertex[k])

    def _validate_common_props(self, vertex, event):
        self.assertEqual(vertex[VProps.VITRAGE_CATEGORY],
                         EntityCategory.RESOURCE)
        self.assertEqual(vertex[VProps.VITRAGE_TYPE],
                         event[StaticFields.TYPE])
        self.assertEqual(vertex[VProps.ID], event[StaticFields.ID])
        self.assertFalse(vertex[VProps.VITRAGE_IS_DELETED])

    def _validate_neighbors(self, neighbors, vertex_id, event):
        for i in range(len(neighbors)):
            self._validate_neighbor(
                neighbors[i],
                event[StaticFields.RELATIONSHIPS][i],
                vertex_id)

    def _validate_neighbor(self, neighbor, rel, vertex_id):
        vertex = neighbor.vertex
        self._validate_neighbor_vertex_props(
            vertex,
            rel[StaticFields.TARGET])

        edge = neighbor.edge
        self.assertEqual(edge.source_id, vertex_id)
        self.assertEqual(edge.target_id, neighbor.vertex.vertex_id)
        self.assertEqual(edge.label,
                         rel[StaticFields.RELATIONSHIP_TYPE])

    def _validate_neighbor_vertex_props(self, vertex, event):
        self._validate_common_props(vertex, event)
        self.assertTrue(vertex[VProps.VITRAGE_IS_PLACEHOLDER])
