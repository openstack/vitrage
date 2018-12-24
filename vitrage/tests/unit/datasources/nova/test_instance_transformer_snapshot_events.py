# Copyright 2018 - Nokia
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
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests.mocks import mock_driver as mock_sync
from vitrage.tests.unit.datasources.nova.base_nova_instance_transformer \
    import BaseNovaInstanceTransformerTest

LOG = logging.getLogger(__name__)


# noinspection PyProtectedMember
class NovaInstanceTransformerSnapshotTest(
        BaseNovaInstanceTransformerTest):

    DEFAULT_GROUP_OPTS = [
        cfg.BoolOpt('use_nova_versioned_notifications',
                    default=False),
    ]

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(NovaInstanceTransformerSnapshotTest, cls).setUpClass()

    def test_snapshot_event_transform(self):
        LOG.debug('Test tactual transform action for '
                  'snapshot and snapshot init events')

        # Test setup
        spec_list = mock_sync.simple_instance_generators(
            host_num=1, vm_num=1, snapshot_events=10)
        instance_events = mock_sync.generate_random_events_list(spec_list)

        for event in instance_events:
            # Test action
            transformer = self.transformers[NOVA_INSTANCE_DATASOURCE]
            wrapper = transformer.transform(event)

            # Test assertions
            self._validate_snapshot_vertex_props(
                transformer, wrapper.vertex, event)

            self.assertThat(wrapper.neighbors, matchers.HasLength(1),
                            'Instance has only one host neighbor')
            host_neighbor = wrapper.neighbors[0]
            self._validate_host_neighbor(host_neighbor, event)

            datasource_action = event[DSProps.DATASOURCE_ACTION]
            if datasource_action == DatasourceAction.INIT_SNAPSHOT:
                self.assertEqual(GraphAction.CREATE_ENTITY, wrapper.action)
            elif datasource_action == DatasourceAction.SNAPSHOT:
                self.assertEqual(GraphAction.UPDATE_ENTITY, wrapper.action)

    def test_create_host_neighbor(self):
        LOG.debug('Test create host neighbor')

        # Test setup
        host_name = 'host123'
        vertex_key = 'RESOURCE:nova.instance:instance321'
        vertex_id = \
            TransformerBase.uuid_from_deprecated_vitrage_id(vertex_key)
        time = datetime.datetime.utcnow()
        entity_event = {
            '_info': {
                'host_name': host_name
            },
            DSProps.DATASOURCE_ACTION: 'SNAPSHOT',
            'id': 'instance321',
            DSProps.SAMPLE_DATE: time
        }

        # Test action
        instance_transformer = self.transformers[NOVA_INSTANCE_DATASOURCE]
        neighbor = \
            instance_transformer._create_neighbor(entity_event,
                                                  host_name,
                                                  NOVA_HOST_DATASOURCE,
                                                  EdgeLabel.CONTAINS,
                                                  is_entity_source=False)

        # Test assertions
        host_vertex_id = \
            TransformerBase.uuid_from_deprecated_vitrage_id(
                'RESOURCE:nova.host:host123')
        self.assertEqual(host_vertex_id, neighbor.vertex.vertex_id)
        self.assertEqual(
            time,
            neighbor.vertex.get(VProps.VITRAGE_SAMPLE_TIMESTAMP)
        )

        # test relation edge
        self.assertEqual(host_vertex_id, neighbor.edge.source_id)
        self.assertEqual(vertex_id, neighbor.edge.target_id)
        self.assertEqual(EdgeLabel.CONTAINS, neighbor.edge.label)

    def test_create_placeholder_vertex(self):
        self._test_create_placeholder_vertex()

    def test_create_entity_key(self):
        self._test_create_entity_key()

    def test_build_instance_key(self):
        self._test_build_instance_key()

    @classmethod
    def _get_default_group_opts(cls):
        return cls.DEFAULT_GROUP_OPTS
