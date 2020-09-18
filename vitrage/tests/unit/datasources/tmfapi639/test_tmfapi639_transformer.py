# Copyright 2020
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
from vitrage.common.constants import UpdateMethod

from vitrage.datasources.tmfapi639 import TMFAPI639_DATASOURCE
from vitrage.datasources.tmfapi639.transformer import TmfApi639Transformer
from vitrage.datasources import transformer_base
from vitrage.datasources.transformer_base import TransformerBase

from vitrage.tests.unit.datasources.test_transformer_base import \
    BaseTransformerTest

from datetime import datetime
from json import loads

LOG = logging.getLogger(__name__)

message = '[{"id":"1","name":"Host-1","@type":"Host",\
    "resourceRelationship":[{"type":"parent","resource":{"id":"1"}}]},\
            {"id":"2","name":"Host-2","@type":"Host",\
            "resourceRelationship":[{"type":"parent","resource":{"id":"1"}}]}]'


# noinspection PyProtectedMember
class TestTmfApi639Transformer(BaseTransformerTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PULL),
    ]

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(TestTmfApi639Transformer, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=TMFAPI639_DATASOURCE)
        cls.transformer = TmfApi639Transformer(cls.transformers)
        cls.transformers[TMFAPI639_DATASOURCE] = cls.transformer

    # noinspection PyAttributeOutsideInit
    def setUp(self):
        super(TestTmfApi639Transformer, self).setUp()
        self.timestamp = datetime.utcnow()

    def test_create_entity_key(self):
        event = loads(message)[0]
        self.assertIsNotNone(event)

        transformer = TmfApi639Transformer(self.transformers)
        observed_key = transformer._create_entity_key(event)

        entity_type = TMFAPI639_DATASOURCE
        entity_id = event["id"]

        # Test assertions
        observed_key_fields = observed_key.split(
            TransformerBase.KEY_SEPARATOR)

        self.assertEqual(entity_type, observed_key_fields[1])
        self.assertEqual(entity_id, observed_key_fields[2])

    # Transformer tests:
    # - Vertex creation
    # - Neighbor link

    def test_topology(self):

        sample_timestamp = \
            datetime.now().strftime(transformer_base.TIMESTAMP_FORMAT)
        update_timestamp = TransformerBase._format_update_timestamp(
            update_timestamp=None,
            sample_timestamp=sample_timestamp)

        transformer = self.transformers[TMFAPI639_DATASOURCE]

        # Create 1 vertex
        event1 = loads(message)[0]
        event1[DSProps.DATASOURCE_ACTION] = DatasourceAction.SNAPSHOT
        event1[DSProps.SAMPLE_DATE] = update_timestamp
        self.assertIsNotNone(event1)

        # Create vertex 1
        wrapper1 = transformer.transform(event1)
        # Assertion
        self._validate_base_vertex_props(
            wrapper1.vertex,
            event1["name"],
            TMFAPI639_DATASOURCE
        )

        # Create 2nd vertex
        event2 = loads(message)[1]
        event2[DSProps.DATASOURCE_ACTION] = DatasourceAction.SNAPSHOT
        event2[DSProps.SAMPLE_DATE] = update_timestamp
        self.assertIsNotNone(event2)

        # Create vertex 2
        wrapper2 = transformer.transform(event2)
        # Assertion
        self._validate_base_vertex_props(
            wrapper2.vertex,
            event2["name"],
            TMFAPI639_DATASOURCE
        )

        # Test whether they are linked
        self.assertThat(wrapper2.neighbors, matchers.HasLength(1))

        parent_id = transformer._create_entity_key(event1)
        parent_uuid = \
            transformer.uuid_from_deprecated_vitrage_id(parent_id)

        child_id = transformer._create_entity_key(event2)
        child_uuid = \
            transformer.uuid_from_deprecated_vitrage_id(child_id)

        self.assertEqual(wrapper2.neighbors[0].edge.source_id, child_uuid)
        self.assertEqual(wrapper2.neighbors[0].edge.target_id, parent_uuid)
