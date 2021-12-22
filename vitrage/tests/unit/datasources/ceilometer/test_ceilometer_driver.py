# Copyright 2017 - ZTE, Nokia
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
import testtools

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import UpdateMethod
from vitrage.datasources.ceilometer import CEILOMETER_DATASOURCE
from vitrage.datasources.ceilometer.properties import CeilometerEventType
from vitrage.datasources.ceilometer.properties \
    import CeilometerProperties as CeilProps
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver
from vitrage.tests.unit.datasources.ceilometer.mock_driver \
    import MockCeilometerDriver


@testtools.skip("skip for now")
class CeilometerDriverTest(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH),
    ]

    # noinspection PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(CeilometerDriverTest, cls).setUpClass()
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=CEILOMETER_DATASOURCE)

    def test_event_alarm_notifications(self):

        aodh_driver = MockCeilometerDriver()

        # 1. alarm creation with 'ok' state
        # prepare data
        detail_data = {"type": "creation",
                       CeilProps.DETAIL: self._create_alarm_data_type_event(),
                       }
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, CeilometerEventType.CREATION)

        # Test assertions
        # alarm with status OK should not be handled
        self.assertIsNone(entity)

        # 2.alarm state transition from 'ok' to 'alarm'
        detail_data = {"type": "state transition",
                       CeilProps.DETAIL: {CeilProps.STATE: "alarm"}}
        alarm.update(detail_data)
        entity = aodh_driver.enrich_event(alarm,
                                          CeilometerEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: ok->alarm, need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[CeilProps.STATE],
                         alarm[CeilProps.DETAIL][CeilProps.STATE])
        self.assertEqual(entity[CeilProps.SEVERITY],
                         alarm[CeilProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         CeilometerEventType.STATE_TRANSITION)

        # 3. delete alarm which is 'alarm' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.DELETION)

        # Test assertions
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         CeilometerEventType.DELETION)

        # 4. alarm creation with 'alarm' state
        # prepare data
        detail_data = {"type": "creation",
                       CeilProps.DETAIL:
                           self._create_alarm_data_type_event(state="alarm")}
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.CREATION)

        # Test assertions
        # alarm with status 'alarm' need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[CeilProps.STATE],
                         alarm[CeilProps.DETAIL][CeilProps.STATE])
        self.assertEqual(entity[CeilProps.SEVERITY],
                         alarm[CeilProps.SEVERITY])
        self.assertIsNone(entity[CeilProps.RESOURCE_ID])
        self.assertEqual("*", entity[CeilProps.EVENT_TYPE])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         CeilometerEventType.CREATION)

        # 5. alarm rule change
        # prepare data
        detail_data = {"type": "rule change",
                       CeilProps.DETAIL: {
                           "severity": "critical",
                           CeilProps.RULE:
                               {"query": [{"field": "traits.resource_id",
                                           "type": "",
                                           "value": "1",
                                           "op": "eq"}],
                                "event_type": "instance.update"}}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.RULE_CHANGE)

        # Test assertions
        # alarm rule change: need to be update
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[CeilProps.SEVERITY],
                         alarm[CeilProps.DETAIL][CeilProps.SEVERITY])
        self.assertEqual(
            entity[CeilProps.EVENT_TYPE],
            alarm[CeilProps.DETAIL][CeilProps.RULE][CeilProps.EVENT_TYPE])
        self.assertEqual("1", entity[CeilProps.RESOURCE_ID])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         CeilometerEventType.RULE_CHANGE)

        # 6. alarm state change from 'alarm' to 'ok'
        # prepare data
        detail_data = {"type": "state transition",
                       CeilProps.DETAIL: {CeilProps.STATE: "ok"}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: alarm->OK, need to be deleted
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         CeilometerEventType.STATE_TRANSITION)

        # 7. delete alarm which is 'ok' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.DELETION)

        # Test assertions
        self.assertIsNone(entity)

    def test_gnocchi_threshold_alarm_notifications(self):
        aodh_driver = MockCeilometerDriver()

        # 1. alarm creation with 'ok' state
        # prepare data
        detail_data = {"type": "gnocchi_resources_threshold",
                       CeilProps.DETAIL: self._create_alarm_data_gnocchi()}
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.CREATION)

        # Test assertions
        # alarm with status OK should not be handled
        self.assertIsNone(entity)

        # 2.alarm state transition from 'ok' to 'alarm'
        detail_data = {"type": "state transition",
                       CeilProps.DETAIL: {CeilProps.STATE: "alarm"}}
        alarm.update(detail_data)
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: ok->alarm, need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[CeilProps.STATE],
                         alarm[CeilProps.DETAIL][CeilProps.STATE])
        self.assertEqual(entity[CeilProps.SEVERITY],
                         alarm[CeilProps.SEVERITY])

        # 3. delete alarm which is 'alarm' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.DELETION)

        # Test assertions
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         CeilometerEventType.DELETION)

        # 4. alarm creation with 'alarm' state
        # prepare data
        detail_data = {"type": "gnocchi_resources_threshold",
                       CeilProps.DETAIL:
                           self._create_alarm_data_gnocchi(state="alarm")}
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.CREATION)

        # Test assertions
        # alarm with status 'alarm' need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[CeilProps.STATE],
                         alarm[CeilProps.DETAIL][CeilProps.STATE])
        self.assertEqual(entity[CeilProps.SEVERITY],
                         alarm[CeilProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         CeilometerEventType.CREATION)

        # 5. alarm rule change
        # prepare data
        detail_data = {"type": "rule change",
                       CeilProps.DETAIL: {
                           "severity": "critical",
                           CeilProps.RULE:
                               {"granularity": "300",
                                "threshold": "0.0123",
                                "comparison_operator": "eq"}}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.RULE_CHANGE)

        # Test assertions
        # alarm rule change: need to be update
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[CeilProps.SEVERITY],
                         alarm[CeilProps.DETAIL][CeilProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         CeilometerEventType.RULE_CHANGE)

        # 6. alarm state change from 'alarm' to 'ok'
        # prepare data
        detail_data = {"type": "state transition",
                       CeilProps.DETAIL: {CeilProps.STATE: "ok"}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(
            alarm,
            CeilometerEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: alarm->OK, need to be deleted
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         CeilometerEventType.STATE_TRANSITION)

        # 7. delete alarm which is 'ok' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(
            alarm, CeilometerEventType.DELETION)

        # Test assertions
        self.assertIsNone(entity)

    def _create_alarm_data_gnocchi(self,
                                   state="ok",
                                   type="gnocchi_resources_threshold",
                                   rule=None):

        if rule is None:
            rule = {"granularity": "300",
                    "threshold": "0.001",
                    "comparison_operator": "gt",
                    "resource_type": "instance"
                    }
        return {CeilProps.DESCRIPTION: "test",
                CeilProps.TIMESTAMP: "2016-11-09T01:39:13.839584",
                CeilProps.ENABLED: True,
                CeilProps.STATE_TIMESTAMP: "2016-11-09T01:39:13.839584",
                CeilProps.ALARM_ID: "7e5c3754-e2eb-4782-ae00-7da5ded8568b",
                CeilProps.REPEAT_ACTIONS: False,
                CeilProps.PROJECT_ID: "c365d18fcc03493187016ae743f0cc4d",
                CeilProps.NAME: "test",
                CeilProps.SEVERITY: "low",
                CeilProps.RESOURCE_ID: "88cd2d1d-8af4-4d00-9b5e-f82f8c8b0f8d",
                CeilProps.TYPE: type,
                CeilProps.STATE: state,
                CeilProps.RULE: rule,
                CeilProps.STATE_REASON: 'for test'}

    def _create_alarm_data_type_event(self,
                                      state="ok",
                                      type="event",
                                      rule=None):

        if rule is None:
            rule = {"query": [], "event_type": "*"}
        return {CeilProps.DESCRIPTION: "test",
                CeilProps.TIMESTAMP: "2016-11-09T01:39:13.839584",
                CeilProps.ENABLED: True,
                CeilProps.STATE_TIMESTAMP: "2016-11-09T01:39:13.839584",
                CeilProps.ALARM_ID: "7e5c3754-e2eb-4782-ae00-7da5ded8568b",
                CeilProps.REPEAT_ACTIONS: False,
                CeilProps.PROJECT_ID: "c365d18fcc03493187016ae743f0cc4d",
                CeilProps.NAME: "test",
                CeilProps.SEVERITY: "low",
                CeilProps.TYPE: type,
                CeilProps.STATE: state,
                CeilProps.RULE: rule,
                CeilProps.STATE_REASON: 'for test'}

    def _validate_aodh_entity_comm_props(self, entity, alarm):

        self.assertEqual(entity[CeilProps.ALARM_ID],
                         alarm[CeilProps.ALARM_ID])
        self.assertEqual(entity[CeilProps.PROJECT_ID],
                         alarm[CeilProps.PROJECT_ID])
        self.assertEqual(entity[CeilProps.TIMESTAMP],
                         alarm[CeilProps.TIMESTAMP])
        self.assertEqual(entity[CeilProps.DESCRIPTION],
                         alarm[CeilProps.DETAIL][CeilProps.DESCRIPTION])
        self.assertEqual(entity[CeilProps.ENABLED],
                         alarm[CeilProps.DETAIL][CeilProps.ENABLED])
        self.assertEqual(entity[CeilProps.NAME],
                         alarm[CeilProps.DETAIL][CeilProps.NAME])
        self.assertEqual(entity[CeilProps.REPEAT_ACTIONS],
                         alarm[CeilProps.DETAIL][CeilProps.REPEAT_ACTIONS])
        self.assertEqual(entity[CeilProps.TYPE],
                         alarm[CeilProps.DETAIL][CeilProps.TYPE])
