# Copyright 2018 - Nokia, ZTE
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
from vitrage.datasources.static.transformer import StaticTransformer

LOG = logging.getLogger(__name__)


class MockTransformer(StaticTransformer):

    def __init__(self, transformers):
        super(MockTransformer, self).__init__(transformers)

    def _create_vertex(self, entity_event):
        vertex = super(MockTransformer, self)._create_vertex(entity_event)
        for k, v in vertex.items():
            if isinstance(v, list):
                vertex[k] = tuple(v)
        return vertex
