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

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps


from vitrage.datasources.resource_transformer_base import \
    ResourceTransformerBase
from vitrage.datasources.transformer_base import extract_field_value
import vitrage.graph.utils as graph_utils

from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import transformer_base as tbase

from vitrage.datasources.kubernetes.properties import KUBERNETES_DATASOURCE
from vitrage.datasources.kubernetes.properties import \
    KubernetesProperties as kubProp
from vitrage.utils import file as file_utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class KubernetesTransformer(ResourceTransformerBase):

    def _create_vertex(self, entity_event):
        metadata = {
            VProps.NAME: self._get_cluster_name(),
        }

        entity_key = self._create_entity_key(entity_event)

        vitrage_sample_timestamp = entity_event[DSProps.SAMPLE_DATE]

        update_timestamp = self._format_update_timestamp(
            extract_field_value(entity_event, DSProps.SAMPLE_DATE),
            vitrage_sample_timestamp)

        return graph_utils.create_vertex(
            entity_key,
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=KUBERNETES_DATASOURCE,
            vitrage_sample_timestamp=vitrage_sample_timestamp,
            update_timestamp=update_timestamp,
            metadata=metadata)

    def _create_snapshot_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_node_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_node_neighbors(entity_event)

    def _create_entity_key(self, event):

        key_fields = self._key_values(KUBERNETES_DATASOURCE,
                                      self._get_cluster_name())
        key = tbase.build_key(key_fields)
        return key

    def get_vitrage_type(self):
        return KUBERNETES_DATASOURCE

    def _get_cluster_name(self):
        kubeconf = file_utils.load_yaml_file(CONF.kubernetes.config_file)
        if not kubeconf:
            return None
        contexts = kubeconf['contexts']
        for context in contexts:
            if context['name'] == kubeconf['current-context']:
                cluster_name = context['context']['cluster']
        return cluster_name

    def _create_node_neighbors(self, entity_event):
        """neighbors are existing Nova instances only"""
        neighbors = []
        for neighbor in entity_event[kubProp.RESOURCES]:
            neighbor[DSProps.ENTITY_TYPE] = entity_event[DSProps.ENTITY_TYPE]
            neighbor[DSProps.DATASOURCE_ACTION] = \
                entity_event[DSProps.DATASOURCE_ACTION]
            neighbor[DSProps.SAMPLE_DATE] = entity_event[DSProps.SAMPLE_DATE]

            neighbor_id = neighbor[kubProp.EXTERNALID]
            neighbor_datasource_type = NOVA_INSTANCE_DATASOURCE
            neighbors.append(self._create_neighbor(neighbor,
                                                   neighbor_id,
                                                   neighbor_datasource_type,
                                                   EdgeLabel.COMPRISED,
                                                   is_entity_source=True))

        return neighbors
