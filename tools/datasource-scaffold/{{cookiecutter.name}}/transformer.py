# Copyright 2018 - Vitrage team
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

from oslo_log import log as logging

from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.resource_transformer_base import \
    ResourceTransformerBase
from vitrage.datasources.{{cookiecutter.name}} import {{cookiecutter.name|upper}}_DATASOURCE
from vitrage.datasources.{{cookiecutter.name}} import {{cookiecutter.name|capitalize}}Fields
from vitrage.datasources import transformer_base
import vitrage.graph.utils as graph_utils

LOG = logging.getLogger(__name__)


class {{cookiecutter.name|capitalize}}Transformer(ResourceTransformerBase):

    def __init__(self, transformers:
        super({{cookiecutter.name|capitalize}}Transformer, self).__init__(transformers)

    def _create_snapshot_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_update_entity_vertex(self, entity_event):
        return self._create_vertex(entity_event)

    def _create_snapshot_neighbors(self, entity_event):
        return self._create_{{cookiecutter.name}}_neighbors(entity_event)

    def _create_update_neighbors(self, entity_event):
        return self._create_{{cookiecutter.name}}_neighbors(entity_event)

    def _create_entity_key(self, entity_event):
        """the unique key of this entity"""

        # FIXME: Below is just an example. It could be different in a real
        #        datasource
        entity_id = entity_event[VProps.ID]
        entity_type = entity_event[{{cookiecutter.name|capitalize}}Fields.TYPE]
        key_fields = self._key_values(entity_type, entity_id)
        return transformer_base.build_key(key_fields)

    @staticmethod
    def get_vitrage_type():
        return {{cookiecutter.name|upper}}_DATASOURCE

    def _create_vertex(self, entity_event):
        return graph_utils.create_vertex(
            self._create_entity_key(entity_event),
            vitrage_category=EntityCategory.RESOURCE,
            vitrage_type=None,  # FIXME
            vitrage_{{cookiecutter.name}}_timestamp=None,  # FIXME
            entity_id=None,  # FIXME
            update_timestamp=None,  # FIXME
            entity_state=None,  # FIXME
            metadata=None)  # FIXME

    def _create_{{cookiecutter.name}}_neighbors(self, entity_event):
        return []
