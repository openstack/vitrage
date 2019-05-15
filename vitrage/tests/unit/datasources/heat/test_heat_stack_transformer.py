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
from oslo_log import log as logging
from testtools import matchers

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import UpdateMethod
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.cinder.volume import CINDER_VOLUME_DATASOURCE
from vitrage.datasources.cinder.volume.transformer \
    import CinderVolumeTransformer
from vitrage.datasources.heat.stack import HEAT_STACK_DATASOURCE
from vitrage.datasources.heat.stack.transformer import HeatStackTransformer
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.nova.instance.transformer import InstanceTransformer
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver as mock_sync

LOG = logging.getLogger(__name__)


class TestHeatStackTransformer(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH),
    ]

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(TestHeatStackTransformer, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=HEAT_STACK_DATASOURCE)
        cls.transformers[HEAT_STACK_DATASOURCE] = \
            HeatStackTransformer(cls.transformers)
        cls.transformers[CINDER_VOLUME_DATASOURCE] = \
            CinderVolumeTransformer(cls.transformers)
        cls.transformers[NOVA_INSTANCE_DATASOURCE] = \
            InstanceTransformer(cls.transformers)

    def test_create_placeholder_vertex(self):
        LOG.debug('Heat Stack transformer test: Create placeholder vertex')

        # Tests setup
        stack_id = 'Stack123'
        timestamp = datetime.datetime.utcnow()
        properties = {
            VProps.ID: stack_id,
            VProps.VITRAGE_TYPE: HEAT_STACK_DATASOURCE,
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_SAMPLE_TIMESTAMP: timestamp
        }
        transformer = self.transformers[HEAT_STACK_DATASOURCE]

        # Test action
        placeholder = \
            transformer.create_neighbor_placeholder_vertex(**properties)

        # Test assertions
        observed_uuid = placeholder.vertex_id
        expected_key = tbase.build_key(transformer._key_values(
            HEAT_STACK_DATASOURCE,
            stack_id))
        expected_uuid = \
            TransformerBase.uuid_from_deprecated_vitrage_id(expected_key)
        self.assertEqual(expected_uuid, observed_uuid)

        observed_time = placeholder.get(VProps.VITRAGE_SAMPLE_TIMESTAMP)
        self.assertEqual(timestamp, observed_time)

        observed_type = placeholder.get(VProps.VITRAGE_TYPE)
        self.assertEqual(HEAT_STACK_DATASOURCE, observed_type)

        observed_entity_id = placeholder.get(VProps.ID)
        self.assertEqual(stack_id, observed_entity_id)

        observed_vitrage_category = placeholder.get(VProps.VITRAGE_CATEGORY)
        self.assertEqual(EntityCategory.RESOURCE, observed_vitrage_category)

        vitrage_is_placeholder = placeholder.get(VProps.VITRAGE_IS_PLACEHOLDER)
        self.assertTrue(vitrage_is_placeholder)

    def test_key_values(self):
        LOG.debug('Heat Stack transformer test: get key values')

        # Test setup
        volume_type = HEAT_STACK_DATASOURCE
        volume_id = '12345'
        transformer = self.transformers[HEAT_STACK_DATASOURCE]

        # Test action
        observed_key_fields = transformer._key_values(volume_type,
                                                      volume_id)

        # Test assertions
        self.assertEqual(EntityCategory.RESOURCE, observed_key_fields[0])
        self.assertEqual(HEAT_STACK_DATASOURCE, observed_key_fields[1])
        self.assertEqual(volume_id, observed_key_fields[2])

    def test_snapshot_transform(self):
        LOG.debug('Heat Stack transformer test: transform entity event '
                  'snapshot')

        # Test setup
        spec_list = \
            mock_sync.simple_stack_generators(stack_num=3,
                                              instance_and_volume_num=7,
                                              snapshot_events=7)
        static_events = mock_sync.generate_random_events_list(spec_list)

        for event in static_events:
            # Test action
            wrapper = self.transformers[HEAT_STACK_DATASOURCE].transform(
                event)

            # Test assertions
            vertex = wrapper.vertex
            self._validate_stack_vertex_props(vertex, event)

            neighbors = wrapper.neighbors
            self._validate_neighbors(neighbors, vertex.vertex_id, event)

    def test_update_transform(self):
        LOG.debug('Heat Stack transformer test: transform entity event '
                  'update')

        # Test setup
        spec_list = \
            mock_sync.simple_stack_generators(stack_num=3,
                                              instance_and_volume_num=7,
                                              snapshot_events=7)
        static_events = mock_sync.generate_random_events_list(spec_list)

        for event in static_events:
            # Test action
            wrapper = self.transformers[HEAT_STACK_DATASOURCE].transform(
                event)

            # Test assertions
            vertex = wrapper.vertex
            self._validate_stack_vertex_props(vertex, event)

            neighbors = wrapper.neighbors
            self._validate_neighbors(neighbors, vertex.vertex_id, event)

    def _validate_stack_vertex_props(self, vertex, event):

        is_update_event = tbase.is_update_event(event)

        self.assertEqual(EntityCategory.RESOURCE,
                         vertex[VProps.VITRAGE_CATEGORY])
        self.assertEqual(event[DSProps.ENTITY_TYPE],
                         vertex[VProps.VITRAGE_TYPE])

        id_field_path = 'stack_identity' if is_update_event else 'id'
        self.assertEqual(
            tbase.extract_field_value(event, id_field_path),
            vertex[VProps.ID])

        self.assertEqual(event[DSProps.SAMPLE_DATE],
                         vertex[VProps.VITRAGE_SAMPLE_TIMESTAMP])

        name_field_path = 'stack_name'
        self.assertEqual(
            tbase.extract_field_value(event, name_field_path),
            vertex[VProps.NAME])

        state_field_path = 'state' if is_update_event else 'stack_status'
        self.assertEqual(
            tbase.extract_field_value(event, state_field_path),
            vertex[VProps.STATE])

        self.assertFalse(vertex[VProps.VITRAGE_IS_PLACEHOLDER])
        self.assertFalse(vertex[VProps.VITRAGE_IS_DELETED])

    def _validate_neighbors(self, neighbors, stack_vertex_id, event):
        self.assertThat(neighbors, matchers.HasLength(2))

        instance_id = event['resources'][0]['physical_resource_id']
        self._validate_neighbor(neighbors[0],
                                instance_id,
                                NOVA_INSTANCE_DATASOURCE,
                                stack_vertex_id)

        instance_id = event['resources'][1]['physical_resource_id']
        self._validate_neighbor(neighbors[1],
                                instance_id,
                                CINDER_VOLUME_DATASOURCE,
                                stack_vertex_id)

    def _validate_neighbor(self,
                           instance_neighbor,
                           instance_id,
                           datasource_type,
                           stack_vertex_id):
        # validate neighbor vertex
        self.assertEqual(EntityCategory.RESOURCE,
                         instance_neighbor.vertex[VProps.VITRAGE_CATEGORY])
        self.assertEqual(datasource_type,
                         instance_neighbor.vertex[VProps.VITRAGE_TYPE])
        self.assertEqual(instance_id, instance_neighbor.vertex[VProps.ID])
        self.assertTrue(
            instance_neighbor.vertex[VProps.VITRAGE_IS_PLACEHOLDER])
        self.assertFalse(instance_neighbor.vertex[VProps.VITRAGE_IS_DELETED])

        # Validate neighbor edge
        edge = instance_neighbor.edge
        self.assertEqual(edge.target_id, instance_neighbor.vertex.vertex_id)
        self.assertEqual(edge.source_id, stack_vertex_id)
        self.assertEqual(edge.label, EdgeLabel.COMPRISED)
