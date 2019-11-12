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


from oslo_config import cfg
from oslo_log import log as logging
from testtools import matchers

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import GraphAction
from vitrage.common.constants import UpdateMethod
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.kubernetes.properties import KUBERNETES_DATASOURCE
from vitrage.datasources.kubernetes.properties import KubernetesProperties \
    as kubProp
from vitrage.datasources.kubernetes.transformer import KubernetesTransformer
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.nova.instance.transformer import InstanceTransformer
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver as mock_sync
from vitrage.tests.mocks import utils

LOG = logging.getLogger(__name__)

cluster_name = 'kubernetes'


class KubernetesTransformerTest(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PULL),
        cfg.StrOpt(DSOpts.CONFIG_FILE,
                   default=utils.get_resources_dir() +
                   '/kubernetes/kubernetes_config.yaml'),
    ]

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(KubernetesTransformerTest, cls).setUpClass()
        cls.transformers = {}
        cls.transformers[KUBERNETES_DATASOURCE] = KubernetesTransformer(
            cls.transformers)
        cls.transformers[NOVA_INSTANCE_DATASOURCE] = \
            InstanceTransformer(cls.transformers)

    def setUp(self):
        super(KubernetesTransformerTest, self).setUp()
        self.conf_reregister_opts(self.OPTS, group=KUBERNETES_DATASOURCE)

    def test_snapshot_event_transform(self):
        LOG.debug('Test tactual transform action for '
                  'snapshot and snapshot init events')

        k8s_spec_list = \
            mock_sync.simple_k8s_nodes_generators(nodes_num=2,
                                                  snapshot_events=1)

        nodes_events = mock_sync.generate_random_events_list(k8s_spec_list)

        for event in nodes_events:

            k8s_wrapper = self.transformers[KUBERNETES_DATASOURCE].transform(
                event)

            # Test assertions
            self.assertEqual(cluster_name, k8s_wrapper.vertex[VProps.NAME])
            n_length = str(len(k8s_wrapper.neighbors))
            self.assertThat(n_length, matchers.HasLength(1),
                            'Cluster vertex has one neighbor')
            self._validate_cluster_neighbors(k8s_wrapper.neighbors, event)
            datasource_action = event[DSProps.DATASOURCE_ACTION]
            if datasource_action == DatasourceAction.INIT_SNAPSHOT:
                self.assertEqual(GraphAction.CREATE_ENTITY, k8s_wrapper.action)
            elif datasource_action == DatasourceAction.SNAPSHOT:
                self.assertEqual(GraphAction.UPDATE_ENTITY, k8s_wrapper.action)

    def test_build_cluster_key(self):
        LOG.debug('Test build cluster key')

        # Test setup
        expected_key = 'RESOURCE:kubernetes:kubernetes'

        instance_transformer = self.transformers[NOVA_INSTANCE_DATASOURCE]
        # Test action
        key_fields = instance_transformer._key_values(
            KUBERNETES_DATASOURCE,
            cluster_name)

        # Test assertions
        observed_key = tbase.build_key(key_fields)
        self.assertEqual(expected_key, observed_key)

    def _validate_cluster_neighbors(self, neighbor, event):

        # Create expected neighbor
        time = event[DSProps.SAMPLE_DATE]
        external_id = event['resources'][0][kubProp.EXTERNALID]
        properties = {
            VProps.ID: external_id,
            VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE,
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_SAMPLE_TIMESTAMP: time
        }
        nova_instance_tran = self.transformers[NOVA_INSTANCE_DATASOURCE]
        expected_neighbor = \
            nova_instance_tran.create_neighbor_placeholder_vertex(**properties)
        self.assertEqual(expected_neighbor, neighbor[0].vertex)

        # Validate neighbor edge
        edge = neighbor[0].edge
        entity_key = \
            self.transformers[KUBERNETES_DATASOURCE]._create_entity_key(event)
        entity_uuid = \
            TransformerBase.uuid_from_deprecated_vitrage_id(entity_key)
        self.assertEqual(edge.source_id, entity_uuid)
        self.assertEqual(edge.target_id, neighbor[0].vertex.vertex_id)

    def test_create_entity_key(self):
        LOG.debug('Test get key from kubernetes transformer')

        # Test setup
        spec_list = mock_sync.simple_k8s_nodes_generators(nodes_num=1,
                                                          snapshot_events=1)

        nodes_events = mock_sync.generate_random_events_list(spec_list)

        kubernetes_transformer = self.transformers[KUBERNETES_DATASOURCE]
        for event in nodes_events:
            # Test action
            observed_key = kubernetes_transformer._create_entity_key(event)

            # Test assertions
            observed_key_fields = observed_key.split(
                TransformerBase.KEY_SEPARATOR)

            self.assertEqual(EntityCategory.RESOURCE, observed_key_fields[0])
            self.assertEqual(
                KUBERNETES_DATASOURCE,
                observed_key_fields[1]
            )

            key_values = kubernetes_transformer._key_values(
                KUBERNETES_DATASOURCE,
                cluster_name)
            expected_key = tbase.build_key(key_values)

            self.assertEqual(expected_key, observed_key)
