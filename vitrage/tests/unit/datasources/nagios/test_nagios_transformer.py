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
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources.nagios.properties import NagiosProperties
from vitrage.datasources.nagios.properties import NagiosTestStatus
from vitrage.datasources.nagios.transformer import NagiosTransformer
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.host.transformer import HostTransformer
from vitrage.datasources import transformer_base as tbase
from vitrage.datasources.transformer_base import TransformerBase
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver as mock_sync
from vitrage.utils import datetime as datetime_utils

LOG = logging.getLogger(__name__)


# noinspection PyProtectedMember
class NagiosTransformerTest(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PULL),
    ]

    # noinspection PyAttributeOutsideInit,PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(NagiosTransformerTest, cls).setUpClass()
        cls.transformers = {}
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=NAGIOS_DATASOURCE)
        cls.transformers[NOVA_HOST_DATASOURCE] = \
            HostTransformer(cls.transformers)

    def test_create_entity_key(self):
        LOG.debug('Test get key from nova instance transformer')

        # Test setup
        spec_list = mock_sync.simple_nagios_alarm_generators(host_num=1,
                                                             events_num=1)
        nagios_alarms = mock_sync.generate_sequential_events_list(spec_list)
        transformer = NagiosTransformer(self.transformers)

        event = nagios_alarms[0]
        # Test action
        observed_key = transformer._create_entity_key(event)

        # Test assertions
        observed_key_fields = observed_key.split(
            TransformerBase.KEY_SEPARATOR)

        self.assertEqual(EntityCategory.ALARM, observed_key_fields[0])
        self.assertEqual(event[DSProps.ENTITY_TYPE], observed_key_fields[1])
        self.assertEqual(event[NagiosProperties.RESOURCE_NAME],
                         observed_key_fields[2])
        self.assertEqual(event[NagiosProperties.SERVICE],
                         observed_key_fields[3])

    def test_nagios_alarm_transform(self):
        LOG.debug('Nagios alarm transformer test: transform entity event')

        # Test setup
        spec_list = mock_sync.simple_nagios_alarm_generators(host_num=4,
                                                             events_num=10)
        nagios_alarms = mock_sync.generate_sequential_events_list(spec_list)

        transformer = NagiosTransformer(self.transformers)

        for alarm in nagios_alarms:

            cur_alarm_uuid = None

            if alarm.get(NagiosProperties.STATUS) == NagiosTestStatus.OK:
                alarm_key = transformer._create_entity_key(alarm)
                cur_alarm_uuid = \
                    TransformerBase.uuid_from_deprecated_vitrage_id(
                        alarm_key)

            # Test action
            wrapper = transformer.transform(alarm)

            self._validate_vertex(wrapper.vertex, alarm)

            neighbors = wrapper.neighbors
            self.assertThat(neighbors, matchers.HasLength(1))
            neighbor = neighbors[0]

            # Right now we are support only host as a resource
            if neighbor.vertex[VProps.VITRAGE_TYPE] == NOVA_HOST_DATASOURCE:
                self._validate_host_neighbor(
                    neighbors[0], alarm, cur_alarm_uuid)

            self._validate_action(alarm, wrapper)

    def _validate_action(self, alarm, wrapper):
        ds_action = alarm[DSProps.DATASOURCE_ACTION]
        if ds_action in (DatasourceAction.SNAPSHOT, DatasourceAction.UPDATE):
            if alarm[NagiosProperties.STATUS] == NagiosTestStatus.OK:
                self.assertEqual(GraphAction.DELETE_ENTITY, wrapper.action)
            else:
                self.assertEqual(GraphAction.UPDATE_ENTITY, wrapper.action)
        else:
            self.assertEqual(GraphAction.CREATE_ENTITY, wrapper.action)

    def _validate_vertex(self, vertex, event):

        self.assertEqual(EntityCategory.ALARM, vertex[VProps.VITRAGE_CATEGORY])
        self.assertEqual(event[DSProps.ENTITY_TYPE],
                         vertex[VProps.VITRAGE_TYPE])
        self.assertEqual(event[NagiosProperties.SERVICE], vertex[VProps.NAME])
        self.assertEqual(datetime_utils.change_to_utc_time_and_format(
            event[NagiosProperties.LAST_CHECK],
            tbase.TIMESTAMP_FORMAT),
            vertex[VProps.UPDATE_TIMESTAMP])
        event_type = event.get(DSProps.EVENT_TYPE, None)
        if event_type is not None:
            self.assertEqual(vertex[VProps.STATE],
                             AlarmProps.INACTIVE_STATE if
                             GraphAction.DELETE_ENTITY == event_type else
                             AlarmProps.ACTIVE_STATE)
        else:
            actual_state = AlarmProps.INACTIVE_STATE if \
                NagiosTestStatus.OK == event[NagiosProperties.STATUS] \
                else AlarmProps.ACTIVE_STATE
            self.assertEqual(vertex[VProps.STATE], actual_state)

        self.assertEqual(event[NagiosProperties.STATUS],
                         vertex[VProps.SEVERITY])

        self.assertEqual(event[NagiosProperties.STATUS_INFO],
                         vertex[VProps.INFO])

        self.assertFalse(vertex[VProps.VITRAGE_IS_DELETED])
        self.assertFalse(vertex[VProps.VITRAGE_IS_PLACEHOLDER])

    def _validate_host_neighbor(self, neighbor, event, cur_alarm_uuid=None):

        host_vertex = neighbor.vertex

        expected_key = tbase.build_key((EntityCategory.RESOURCE,
                                        NOVA_HOST_DATASOURCE,
                                        event[NagiosProperties.RESOURCE_NAME]))
        expected_uuid = self.transformers[NOVA_HOST_DATASOURCE].\
            uuid_from_deprecated_vitrage_id(expected_key)

        self.assertEqual(expected_uuid, host_vertex.vertex_id)
        self.assertEqual(expected_uuid,
                         host_vertex.properties.get(VProps.VITRAGE_ID))

        self.assertFalse(host_vertex[VProps.VITRAGE_IS_DELETED])
        self.assertTrue(host_vertex[VProps.VITRAGE_IS_PLACEHOLDER])

        self.assertEqual(EntityCategory.RESOURCE,
                         host_vertex[VProps.VITRAGE_CATEGORY])
        self.assertEqual(event[NagiosProperties.RESOURCE_NAME],
                         host_vertex[VProps.ID])
        self.assertEqual(NOVA_HOST_DATASOURCE,
                         host_vertex[VProps.VITRAGE_TYPE])

        edge = neighbor.edge
        self.assertEqual(EdgeLabel.ON, edge.label)

        alarm_key = NagiosTransformer(self.transformers).\
            _create_entity_key(event)
        alarm_uuid = cur_alarm_uuid if cur_alarm_uuid else\
            TransformerBase.uuid_from_deprecated_vitrage_id(alarm_key)

        self.assertEqual(alarm_uuid, edge.source_id)
        self.assertEqual(host_vertex.vertex_id, edge.target_id)
