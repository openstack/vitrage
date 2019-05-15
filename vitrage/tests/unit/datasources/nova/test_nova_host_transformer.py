# Copyright 2016 - Alcatel-Lucent
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
from vitrage.common.constants import GraphAction
from vitrage.common.constants import UpdateMethod
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.host.transformer import HostTransformer
from vitrage.datasources.nova.zone import NOVA_ZONE_DATASOURCE
from vitrage.datasources.nova.zone.transformer import ZoneTransformer
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver as mock_sync

LOG = logging.getLogger(__name__)


# noinspection PyProtectedMember
class NovaHostTransformerTest(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH),
    ]

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(NovaHostTransformerTest, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=NOVA_HOST_DATASOURCE)
        cls.transformers[NOVA_ZONE_DATASOURCE] = ZoneTransformer(
            cls.transformers)
        cls.transformers[NOVA_HOST_DATASOURCE] = HostTransformer(
            cls.transformers)

    def test_create_placeholder_vertex(self):
        LOG.debug('Nova host transformer test: Test create placeholder vertex')

        # Test setup
        host_name = 'host123'
        timestamp = datetime.datetime.utcnow()
        host_transformer = self.transformers[NOVA_HOST_DATASOURCE]

        # Test action
        properties = {
            VProps.ID: host_name,
            VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE,
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_SAMPLE_TIMESTAMP: timestamp
        }
        placeholder = \
            host_transformer.create_neighbor_placeholder_vertex(**properties)

        # Test assertions
        observed_uuid = placeholder.vertex_id
        expected_key = tbase.build_key(host_transformer._key_values(
            NOVA_HOST_DATASOURCE,
            host_name))
        expected_uuid = \
            TransformerBase.uuid_from_deprecated_vitrage_id(expected_key)
        self.assertEqual(expected_uuid, observed_uuid)

        observed_time = placeholder.get(VProps.VITRAGE_SAMPLE_TIMESTAMP)
        self.assertEqual(timestamp, observed_time)

        observed_subtype = placeholder.get(VProps.VITRAGE_TYPE)
        self.assertEqual(NOVA_HOST_DATASOURCE, observed_subtype)

        observed_entity_id = placeholder.get(VProps.ID)
        self.assertEqual(host_name, observed_entity_id)

        observed_vitrage_category = placeholder.get(VProps.VITRAGE_CATEGORY)
        self.assertEqual(EntityCategory.RESOURCE, observed_vitrage_category)

        vitrage_is_placeholder = placeholder.get(VProps.VITRAGE_IS_PLACEHOLDER)
        self.assertTrue(vitrage_is_placeholder)

    def test_key_values(self):

        LOG.debug('Test key values')

        # Test setup
        host_name = 'host123456'
        host_transformer = self.transformers[NOVA_HOST_DATASOURCE]

        # Test action
        observed_key_fields = host_transformer._key_values(
            NOVA_HOST_DATASOURCE,
            host_name)

        # Test assertions
        self.assertEqual(EntityCategory.RESOURCE, observed_key_fields[0])
        self.assertEqual(NOVA_HOST_DATASOURCE, observed_key_fields[1])
        self.assertEqual(host_name, observed_key_fields[2])

    def test_snapshot_transform(self):
        LOG.debug('Nova host transformer test: transform entity event')

        # Test setup
        spec_list = mock_sync.simple_host_generators(zone_num=2,
                                                     host_num=4,
                                                     snapshot_events=5)

        host_events = mock_sync.generate_random_events_list(spec_list)

        for event in host_events:
            # Test action
            wrapper = self.transformers[NOVA_HOST_DATASOURCE].transform(event)

            # Test assertions
            self._validate_vertex_props(wrapper.vertex, event)

            neighbors = wrapper.neighbors
            self.assertThat(neighbors, matchers.HasLength(1))
            self._validate_zone_neighbor(neighbors[0], event)

            if DatasourceAction.SNAPSHOT == event[DSProps.DATASOURCE_ACTION]:
                self.assertEqual(GraphAction.UPDATE_ENTITY, wrapper.action)
            else:
                self.assertEqual(GraphAction.CREATE_ENTITY, wrapper.action)

    def _validate_zone_neighbor(self, zone, event):

        zone_name = tbase.extract_field_value(event, 'zone')
        time = event[DSProps.SAMPLE_DATE]

        zt = self.transformers[NOVA_ZONE_DATASOURCE]
        properties = {
            VProps.ID: zone_name,
            VProps.VITRAGE_TYPE: NOVA_ZONE_DATASOURCE,
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_SAMPLE_TIMESTAMP: time
        }
        expected_neighbor = \
            zt.create_neighbor_placeholder_vertex(**properties)
        self.assertEqual(expected_neighbor, zone.vertex)

        # Validate neighbor edge
        edge = zone.edge
        transformer = self.transformers[NOVA_HOST_DATASOURCE]
        entity_key = transformer._create_entity_key(event)
        entity_uuid = \
            TransformerBase.uuid_from_deprecated_vitrage_id(entity_key)
        self.assertEqual(edge.source_id, zone.vertex.vertex_id)
        self.assertEqual(edge.target_id, entity_uuid)
        self.assertEqual(edge.label, EdgeLabel.CONTAINS)

    def _validate_vertex_props(self, vertex, event):

        extract_value = tbase.extract_field_value

        expected_id = extract_value(event, 'host')
        observed_id = vertex[VProps.ID]
        self.assertEqual(expected_id, observed_id)
        self.assertEqual(
            EntityCategory.RESOURCE,
            vertex[VProps.VITRAGE_CATEGORY]
        )

        self.assertEqual(
            NOVA_HOST_DATASOURCE,
            vertex[VProps.VITRAGE_TYPE]
        )

        expected_timestamp = event[DSProps.SAMPLE_DATE]
        observed_timestamp = vertex[VProps.VITRAGE_SAMPLE_TIMESTAMP]
        self.assertEqual(expected_timestamp, observed_timestamp)

        expected_name = extract_value(event, 'host')
        observed_name = vertex[VProps.NAME]
        self.assertEqual(expected_name, observed_name)

        vitrage_is_placeholder = vertex[VProps.VITRAGE_IS_PLACEHOLDER]
        self.assertFalse(vitrage_is_placeholder)

        vitrage_is_deleted = vertex[VProps.VITRAGE_IS_DELETED]
        self.assertFalse(vitrage_is_deleted)

    def test_extract_event_action(self):
        LOG.debug('Test extract event action')

        # Test setup
        spec_list = mock_sync.simple_host_generators(
            zone_num=1,
            host_num=1,
            snapshot_events=1,
            snap_vals={DSProps.DATASOURCE_ACTION: DatasourceAction.SNAPSHOT})

        hosts_events = mock_sync.generate_random_events_list(spec_list)
        host_transformer = self.transformers[NOVA_HOST_DATASOURCE]

        # Test action
        action = host_transformer._extract_graph_action(hosts_events[0])

        # Test assertion
        self.assertEqual(GraphAction.UPDATE_ENTITY, action)

        # Test setup
        spec_list = mock_sync.simple_host_generators(
            zone_num=1,
            host_num=1,
            snapshot_events=1,
            snap_vals={DSProps.DATASOURCE_ACTION:
                       DatasourceAction.INIT_SNAPSHOT})
        hosts_events = mock_sync.generate_random_events_list(spec_list)
        host_transformer = self.transformers[NOVA_HOST_DATASOURCE]

        # Test action
        action = host_transformer._extract_graph_action(hosts_events[0])

        # Test assertions
        self.assertEqual(GraphAction.CREATE_ENTITY, action)

        # TODO(lhartal): To add extract action from update event
