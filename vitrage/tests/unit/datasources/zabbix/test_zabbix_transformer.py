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
from vitrage.datasources.alarm_properties import AlarmProperties as AlarmProps
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.host.transformer import HostTransformer
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.datasources.zabbix.properties import ZabbixProperties\
    as ZabbixProps
from vitrage.datasources.zabbix.properties import ZabbixTriggerSeverity
from vitrage.datasources.zabbix.properties import ZabbixTriggerValue
from vitrage.datasources.zabbix.transformer import ZabbixTransformer
from vitrage.datasources.zabbix import ZABBIX_DATASOURCE
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver as mock_sync
from vitrage.utils.datetime import format_unix_timestamp

LOG = logging.getLogger(__name__)


# noinspection PyProtectedMember
class ZabbixTransformerTest(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PULL),
    ]

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(ZabbixTransformerTest, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=ZABBIX_DATASOURCE)
        cls.transformers[NOVA_HOST_DATASOURCE] = \
            HostTransformer(cls.transformers)

    def test_create_entity_key(self):
        LOG.debug('Test get key from nova instance transformer')

        # Test setup
        spec_list = mock_sync.simple_zabbix_alarm_generators(host_num=1,
                                                             events_num=1)
        zabbix_alarms = mock_sync.generate_sequential_events_list(spec_list)
        transformer = ZabbixTransformer(self.transformers)
        event = zabbix_alarms[0]
        self.enrich_event(event)

        # Test action
        observed_key = transformer._create_entity_key(event)

        # Test assertions
        observed_key_fields = observed_key.split(
            TransformerBase.KEY_SEPARATOR)

        self.assertEqual(EntityCategory.ALARM, observed_key_fields[0])
        self.assertEqual(event[DSProps.ENTITY_TYPE], observed_key_fields[1])
        self.assertEqual(event[ZabbixProps.RESOURCE_NAME],
                         observed_key_fields[2])
        self.assertEqual(event[ZabbixProps.TRIGGER_ID],
                         observed_key_fields[3])

    def test_zabbix_alarm_transform(self):
        LOG.debug('Zabbix alarm transformer test: transform entity event')

        # Test setup
        spec_list = mock_sync.simple_zabbix_alarm_generators(host_num=4,
                                                             events_num=10)
        zabbix_alarms = mock_sync.generate_sequential_events_list(spec_list)

        for alarm in zabbix_alarms:
            # Test action
            self.enrich_event(alarm, format_timestamp=False)
            wrapper = ZabbixTransformer(self.transformers)\
                .transform(alarm)
            self._validate_vertex(wrapper.vertex, alarm)

            neighbors = wrapper.neighbors
            self.assertThat(neighbors, matchers.HasLength(1))
            neighbor = neighbors[0]

            # Right now we are support only host as a resource
            if neighbor.vertex[VProps.VITRAGE_TYPE] == NOVA_HOST_DATASOURCE:
                self._validate_host_neighbor(neighbors[0], alarm)

            self._validate_action(alarm, wrapper)

    def _validate_action(self, alarm, wrapper):
        ds_action = alarm[DSProps.DATASOURCE_ACTION]
        if ds_action in (DatasourceAction.SNAPSHOT, DatasourceAction.UPDATE):
            if alarm[ZabbixProps.VALUE] == ZabbixTriggerValue.OK:
                self.assertEqual(GraphAction.DELETE_ENTITY, wrapper.action)
            else:
                self.assertEqual(GraphAction.UPDATE_ENTITY, wrapper.action)
        else:
            self.assertEqual(GraphAction.CREATE_ENTITY, wrapper.action)

    def _validate_vertex(self, vertex, event):

        self.assertEqual(EntityCategory.ALARM, vertex[VProps.VITRAGE_CATEGORY])
        self.assertEqual(event[DSProps.ENTITY_TYPE],
                         vertex[VProps.VITRAGE_TYPE])
        self.assertEqual(event[ZabbixProps.DESCRIPTION],
                         vertex[VProps.NAME])

        event_status = event[ZabbixProps.VALUE]

        if event_status == ZabbixTriggerValue.OK:
            self.assertEqual(AlarmProps.INACTIVE_STATE,
                             vertex[VProps.STATE])
        else:
            self.assertEqual(AlarmProps.ACTIVE_STATE,
                             vertex[VProps.STATE])

        event_severity = ZabbixTriggerSeverity.str(
            event[ZabbixProps.PRIORITY])
        self.assertEqual(event_severity, vertex[VProps.SEVERITY])

        self.assertFalse(vertex[VProps.VITRAGE_IS_DELETED])
        self.assertFalse(vertex[VProps.VITRAGE_IS_PLACEHOLDER])

    def _validate_host_neighbor(self, neighbor, event):

        host_vertex = neighbor.vertex

        observed_key = host_vertex.vertex_id

        expected_key = tbase.build_key((EntityCategory.RESOURCE,
                                        NOVA_HOST_DATASOURCE,
                                        event[ZabbixProps.RESOURCE_NAME]))
        expected_uuid = \
            TransformerBase.uuid_from_deprecated_vitrage_id(expected_key)

        self.assertEqual(expected_uuid, observed_key)
        self.assertEqual(expected_uuid,
                         host_vertex.properties.get(VProps.VITRAGE_ID))

        self.assertFalse(host_vertex[VProps.VITRAGE_IS_DELETED])
        self.assertTrue(host_vertex[VProps.VITRAGE_IS_PLACEHOLDER])

        self.assertEqual(EntityCategory.RESOURCE,
                         host_vertex[VProps.VITRAGE_CATEGORY])
        self.assertEqual(event[ZabbixProps.RESOURCE_NAME],
                         host_vertex[VProps.ID])
        self.assertEqual(NOVA_HOST_DATASOURCE,
                         host_vertex[VProps.VITRAGE_TYPE])

        edge = neighbor.edge
        self.assertEqual(EdgeLabel.ON, edge.label)

        alarm_key = ZabbixTransformer(self.transformers).\
            _create_entity_key(event)
        alarm_uuid = TransformerBase.uuid_from_deprecated_vitrage_id(alarm_key)
        self.assertEqual(alarm_uuid, edge.source_id)
        self.assertEqual(host_vertex.vertex_id, edge.target_id)

    @staticmethod
    def enrich_event(event, format_timestamp=True):
        if format_timestamp:
            event[ZabbixProps.TIMESTAMP] = format_unix_timestamp(
                event[ZabbixProps.LAST_CHANGE], tbase.TIMESTAMP_FORMAT)
