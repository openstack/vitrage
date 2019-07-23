# Copyright 2019 - Viettel
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
import uuid

from oslo_config import cfg
from oslo_log import log as logging

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import UpdateMethod
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.kapacitor import KAPACITOR_DATASOURCE
from vitrage.datasources.kapacitor.properties import KapacitorProperties \
    as KProps
from vitrage.datasources.kapacitor.properties import KapacitorState \
    as KState
from vitrage.datasources.kapacitor.transformer import KapacitorTransformer
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.host.transformer import HostTransformer
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.nova.instance.transformer import InstanceTransformer
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests.mocks import mock_transformer
from vitrage.tests.unit.datasources.test_alarm_transformer_base import \
    BaseAlarmTransformerTest

LOG = logging.getLogger(__name__)


# noinspection PyProtectedMember
class TestKapacitorTransformer(BaseAlarmTransformerTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH),
    ]

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(TestKapacitorTransformer, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=KAPACITOR_DATASOURCE)
        cls.transformers[KAPACITOR_DATASOURCE] = \
            KapacitorTransformer(cls.transformers)
        cls.transformers[NOVA_INSTANCE_DATASOURCE] = \
            InstanceTransformer(cls.transformers)
        cls.transformers[NOVA_HOST_DATASOURCE] = \
            HostTransformer(cls.transformers)

    def test_create_entity_key(self):
        LOG.debug('Test get key from nova host transformer')

        # Test setup
        host = 'compute-1'
        resource_name = 'compute-1'
        resource_type = 'nova.host'
        update_vals = {KProps.HOST: host,
                       KProps.RESOURCE_TYPE: resource_type,
                       KProps.RESOURCE_NAME: resource_name}

        event = self._generate_event(update_vals)
        transformer = KapacitorTransformer(self.transformers)
        self.assertIsNotNone(event)

        # Test action
        observed_key = transformer._create_entity_key(event)

        # Test assertions
        observed_key_fields = observed_key.split(
            TransformerBase.KEY_SEPARATOR)

        self.assertEqual(EntityCategory.ALARM, observed_key_fields[0])
        self.assertEqual(event[DSProps.ENTITY_TYPE], observed_key_fields[1])
        self.assertEqual(event[KProps.RESOURCE_NAME],
                         observed_key_fields[2])
        self.assertEqual(event[KProps.ID],
                         observed_key_fields[3])

    def test_create_update_entity_vertex(self):
        # Test setup
        host1 = 'host1'
        instance_id = uuid.uuid4().hex
        event_on_host = self._generate_event_on_host(host1)
        event_on_instance = self._generate_event_on_instance(host1,
                                                             instance_id)
        self.assertIsNotNone(event_on_host)
        self.assertIsNotNone(event_on_instance)

        # Test action
        transformer = self.transformers[KAPACITOR_DATASOURCE]
        wrapper_for_host = transformer.transform(event_on_host)
        wrapper_for_instance = transformer.transform(event_on_instance)

        # Test assertions
        self._validate_vertex_props(wrapper_for_host.vertex, event_on_host)
        self._validate_vertex_props(wrapper_for_instance.vertex,
                                    event_on_instance)

        # Validate the neighbors: only one valid host neighbor
        host_entity_key = transformer._create_entity_key(event_on_host)
        host_entity_uuid = \
            transformer.uuid_from_deprecated_vitrage_id(host_entity_key)

        instance_entity_key = transformer._create_entity_key(event_on_instance)
        instance_entity_uuid = \
            transformer.uuid_from_deprecated_vitrage_id(instance_entity_key)

        self._validate_host_neighbor(wrapper_for_host,
                                     host_entity_uuid,
                                     host1)

        self._validate_instance_neighbor(wrapper_for_instance,
                                         instance_entity_uuid,
                                         instance_id)

        # Validate the expected action on the graph - update or delete
        self._validate_graph_action(wrapper_for_host)
        self._validate_graph_action(wrapper_for_instance)

    def _validate_vertex_props(self, vertex, event):
        self._validate_alarm_vertex_props(
            vertex, event[KProps.MESSAGE],
            KAPACITOR_DATASOURCE, event[DSProps.SAMPLE_DATE])

    @staticmethod
    def _generate_event(update_vals):
        generators = mock_transformer.simple_kapacitor_alarm_generators(
            update_vals=update_vals)

        return mock_transformer.generate_random_events_list(generators)[0]

    def _generate_event_on_host(self, hostname):
        # fake query result to be used by the transformer for determining
        # the neighbor
        update_vals = {}
        query_result = [{VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE,
                         VProps.ID: hostname}]

        update_vals[KProps.HOST] = hostname
        update_vals[KProps.RESOURCE_TYPE] = NOVA_HOST_DATASOURCE
        update_vals[KProps.RESOURCE_NAME] = hostname
        update_vals[TransformerBase.QUERY_RESULT] = query_result

        return self._generate_event(update_vals)

    def _generate_event_on_instance(self, hostname, instance_id):
        # fake query result to be used by the transformer for determining
        # the neighbor
        update_vals = {}
        query_result = [{VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE,
                         VProps.ID: instance_id}]

        update_vals[KProps.HOST] = hostname
        update_vals[KProps.RESOURCE_TYPE] = NOVA_INSTANCE_DATASOURCE
        update_vals[KProps.RESOURCE_NAME] = hostname
        update_vals[TransformerBase.QUERY_RESULT] = query_result

        return self._generate_event(update_vals)

    def _is_erroneous(self, vertex):
        return vertex[VProps.SEVERITY] != KState.OK
