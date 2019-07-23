# Copyright 2016 - ZTE, Nokia
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

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import UpdateMethod
from vitrage.datasources.aodh import AODH_DATASOURCE
from vitrage.datasources.aodh.properties import AodhEventType
from vitrage.datasources.aodh.properties import AodhExtendedAlarmType as AType
from vitrage.datasources.aodh.properties import AodhProperties as AodhProps
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver
from vitrage.tests.unit.datasources.aodh.mock_driver import MockAodhDriver


class AodhDriverTest(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH),
    ]

    # noinspection PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(AodhDriverTest, cls).setUpClass()
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group=AODH_DATASOURCE)

    def test_event_alarm_notifications(self):

        aodh_driver = MockAodhDriver()

        # 1. alarm creation with 'ok' state
        # prepare data
        detail_data = {"type": "creation",
                       AodhProps.DETAIL: self._create_alarm_data_type_event()}
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.CREATION)

        # Test assertions
        # alarm with status OK should not be handled
        self.assertIsNone(entity)

        # 2.alarm state transition from 'ok' to 'alarm'
        detail_data = {"type": "state transition",
                       AodhProps.DETAIL: {AodhProps.STATE: "alarm"}}
        alarm.update(detail_data)
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: ok->alarm, need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.STATE],
                         alarm[AodhProps.DETAIL][AodhProps.STATE])
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.STATE_TRANSITION)

        # 3. delete alarm which is 'alarm' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.DELETION)

        # Test assertions
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.DELETION)

        # 4. alarm creation with 'alarm' state
        # prepare data
        detail_data = {"type": "creation",
                       AodhProps.DETAIL:
                           self._create_alarm_data_type_event(state="alarm")}
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.CREATION)

        # Test assertions
        # alarm with status 'alarm' need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.STATE],
                         alarm[AodhProps.DETAIL][AodhProps.STATE])
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.SEVERITY])
        self.assertIsNone(entity[AodhProps.RESOURCE_ID])
        self.assertEqual("*", entity[AodhProps.EVENT_TYPE])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.CREATION)

        # 5. alarm rule change
        # prepare data
        detail_data = {"type": "rule change",
                       AodhProps.DETAIL: {
                           "severity": "critical",
                           AodhProps.RULE:
                               {"query": [{"field": "traits.resource_id",
                                           "type": "",
                                           "value": "1",
                                           "op": "eq"}],
                                "event_type": "instance.update"}}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.RULE_CHANGE)

        # Test assertions
        # alarm rule change: need to be update
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.DETAIL][AodhProps.SEVERITY])
        self.assertEqual(
            entity[AodhProps.EVENT_TYPE],
            alarm[AodhProps.DETAIL][AodhProps.RULE][AodhProps.EVENT_TYPE])
        self.assertEqual("1", entity[AodhProps.RESOURCE_ID])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.RULE_CHANGE)

        # 6. alarm state change from 'alarm' to 'ok'
        # prepare data
        detail_data = {"type": "state transition",
                       AodhProps.DETAIL: {AodhProps.STATE: "ok"}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: alarm->OK, need to be deleted
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.STATE_TRANSITION)

        # 7. delete alarm which is 'ok' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.DELETION)

        # Test assertions
        self.assertIsNone(entity)

    def test_gnocchi_threshold_alarm_notifications(self):
        aodh_driver = MockAodhDriver()

        # 1. alarm creation with 'ok' state
        # prepare data
        detail_data = {"type": "gnocchi_resources_threshold",
                       AodhProps.DETAIL: self._create_alarm_data_gnocchi()}
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.CREATION)

        # Test assertions
        # alarm with status OK should not be handled
        self.assertIsNone(entity)

        # 2.alarm state transition from 'ok' to 'alarm'
        detail_data = {"type": "state transition",
                       AodhProps.DETAIL: {AodhProps.STATE: "alarm"}}
        alarm.update(detail_data)
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: ok->alarm, need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.STATE],
                         alarm[AodhProps.DETAIL][AodhProps.STATE])
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.SEVERITY])

        # 3. delete alarm which is 'alarm' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.DELETION)

        # Test assertions
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.DELETION)

        # 4. alarm creation with 'alarm' state
        # prepare data
        detail_data = {"type": "gnocchi_resources_threshold",
                       AodhProps.DETAIL:
                           self._create_alarm_data_gnocchi(state="alarm")}
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.CREATION)

        # Test assertions
        # alarm with status 'alarm' need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.STATE],
                         alarm[AodhProps.DETAIL][AodhProps.STATE])
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.CREATION)

        # 5. alarm rule change
        # prepare data
        detail_data = {"type": "rule change",
                       AodhProps.DETAIL: {
                           "severity": "critical",
                           AodhProps.RULE:
                               {"granularity": "300",
                                "threshold": "0.0123",
                                "comparison_operator": "eq"}}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.RULE_CHANGE)

        # Test assertions
        # alarm rule change: need to be update
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.DETAIL][AodhProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.RULE_CHANGE)

        # 6. alarm state change from 'alarm' to 'ok'
        # prepare data
        detail_data = {"type": "state transition",
                       AodhProps.DETAIL: {AodhProps.STATE: "ok"}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: alarm->OK, need to be deleted
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.STATE_TRANSITION)

        # 7. delete alarm which is 'ok' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.DELETION)

        # Test assertions
        self.assertIsNone(entity)

    def test_gnocchi_aggregation_by_metrics_alarm_notifications(self):
        aodh_driver = MockAodhDriver()

        # 1. alarm creation with 'ok' state
        # prepare data
        detail_data = {
            "type": AType.GNOCCHI_AGGREGATION_BY_METRICS_THRESHOLD,
            AodhProps.DETAIL: self._create_alarm_data_metrics()
        }
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.CREATION)

        # Test assertions
        # alarm with status OK should not be handled
        self.assertIsNone(entity)

        # 2.alarm state transition from 'ok' to 'alarm'
        detail_data = {"type": "state transition",
                       AodhProps.DETAIL: {AodhProps.STATE: "alarm"}}
        alarm.update(detail_data)
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: ok->alarm, need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.STATE],
                         alarm[AodhProps.DETAIL][AodhProps.STATE])
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.SEVERITY])

        # 3. delete alarm which is 'alarm' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.DELETION)

        # Test assertions
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.DELETION)

        # 4. alarm creation with 'alarm' state
        # prepare data
        detail_data = {
            "type": AType.GNOCCHI_AGGREGATION_BY_METRICS_THRESHOLD,
            AodhProps.DETAIL: self._create_alarm_data_metrics(state="alarm")
        }
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.CREATION)

        # Test assertions
        # alarm with status 'alarm' need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.STATE],
                         alarm[AodhProps.DETAIL][AodhProps.STATE])
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.CREATION)

        # 5. alarm rule change
        # prepare data
        detail_data = {"type": "rule change",
                       AodhProps.DETAIL: {
                           "severity": "critical",
                           AodhProps.RULE:
                               {"granularity": "300",
                                "threshold": "0.0123",
                                "comparison_operator": "eq"}}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.RULE_CHANGE)

        # Test assertions
        # alarm rule change: need to be update
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.DETAIL][AodhProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.RULE_CHANGE)

        # 6. alarm state change from 'alarm' to 'ok'
        # prepare data
        detail_data = {"type": "state transition",
                       AodhProps.DETAIL: {AodhProps.STATE: "ok"}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: alarm->OK, need to be deleted
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.STATE_TRANSITION)

        # 7. delete alarm which is 'ok' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.DELETION)

        # Test assertions
        self.assertIsNone(entity)

    def test_gnocchi_aggregation_by_resource_alarm_notifications(self):
        aodh_driver = MockAodhDriver()

        # 1. alarm creation with 'ok' state
        # prepare data
        detail_data = {
            "type": AType.GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD,
            AodhProps.DETAIL: self._create_alarm_data_resource()
        }
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.CREATION)

        # Test assertions
        # alarm with status OK should not be handled
        self.assertIsNone(entity)

        # 2.alarm state transition from 'ok' to 'alarm'
        detail_data = {"type": "state transition",
                       AodhProps.DETAIL: {AodhProps.STATE: "alarm"}}
        alarm.update(detail_data)
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: ok->alarm, need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.STATE],
                         alarm[AodhProps.DETAIL][AodhProps.STATE])
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.SEVERITY])

        # 3. delete alarm which is 'alarm' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.DELETION)

        # Test assertions
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.DELETION)

        # 4. alarm creation with 'alarm' state
        # prepare data
        detail_data = {
            "type": AType.GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD,
            AodhProps.DETAIL:
            self._create_alarm_data_gnocchi(state="alarm")
        }
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.CREATION)

        # Test assertions
        # alarm with status 'alarm' need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.STATE],
                         alarm[AodhProps.DETAIL][AodhProps.STATE])
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.CREATION)

        # 5. alarm rule change
        # prepare data
        detail_data = {"type": "rule change",
                       AodhProps.DETAIL: {
                           "severity": "critical",
                           AodhProps.RULE:
                               {"granularity": "300",
                                "threshold": "0.0123",
                                "comparison_operator": "eq"}}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.RULE_CHANGE)

        # Test assertions
        # alarm rule change: need to be update
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.DETAIL][AodhProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.RULE_CHANGE)

        # 6. alarm state change from 'alarm' to 'ok'
        # prepare data
        detail_data = {"type": "state transition",
                       AodhProps.DETAIL: {AodhProps.STATE: "ok"}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: alarm->OK, need to be deleted
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.STATE_TRANSITION)

        # 7. delete alarm which is 'ok' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.DELETION)

        # Test assertions
        self.assertIsNone(entity)

    def test_composite_alarm_notifications(self):
        aodh_driver = MockAodhDriver()

        # 1. alarm creation with 'ok' state
        # prepare data
        detail_data = {"type": "composite",
                       AodhProps.DETAIL: self._create_alarm_data_composite()}
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.CREATION)

        # Test assertions
        # alarm with status OK should not be handled
        self.assertIsNone(entity)

        # 2.alarm state transition from 'ok' to 'alarm'
        detail_data = {"type": "state transition",
                       AodhProps.DETAIL: {AodhProps.STATE: "alarm"}}
        alarm.update(detail_data)
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: ok->alarm, need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.STATE],
                         alarm[AodhProps.DETAIL][AodhProps.STATE])
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.SEVERITY])

        # 3. delete alarm which is 'alarm' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.DELETION)

        # Test assertions
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.DELETION)

        # 4. alarm creation with 'alarm' state
        # prepare data
        detail_data = {"type": "composite",
                       AodhProps.DETAIL:
                           self._create_alarm_data_composite(state="alarm")}
        generators = \
            mock_driver.simple_aodh_alarm_notification_generators(
                alarm_num=1,
                update_events=1,
                update_vals=detail_data)
        alarm = mock_driver.generate_sequential_events_list(generators)[0]
        alarm_info = alarm.copy()

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.CREATION)

        # Test assertions
        # alarm with status 'alarm' need to be added
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.STATE],
                         alarm[AodhProps.DETAIL][AodhProps.STATE])
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.CREATION)

        # 5. alarm rule change
        # prepare data
        detail_data = {"type": "rule change",
                       AodhProps.DETAIL: {
                           "severity": "critical",
                           AodhProps.RULE:
                               {"granularity": "300",
                                "threshold": "0.0123",
                                "comparison_operator": "eq"}}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.RULE_CHANGE)

        # Test assertions
        # alarm rule change: need to be update
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[AodhProps.SEVERITY],
                         alarm[AodhProps.DETAIL][AodhProps.SEVERITY])
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.RULE_CHANGE)

        # 6. alarm state change from 'alarm' to 'ok'
        # prepare data
        detail_data = {"type": "state transition",
                       AodhProps.DETAIL: {AodhProps.STATE: "ok"}}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm,
                                          AodhEventType.STATE_TRANSITION)

        # Test assertions
        # alarm state change: alarm->OK, need to be deleted
        self.assertIsNotNone(entity)
        self._validate_aodh_entity_comm_props(entity, alarm_info)
        self.assertEqual(entity[DSProps.EVENT_TYPE],
                         AodhEventType.STATE_TRANSITION)

        # 7. delete alarm which is 'ok' state
        # prepare data
        detail_data = {"type": "deletion"}
        alarm.update(detail_data)

        # action
        entity = aodh_driver.enrich_event(alarm, AodhEventType.DELETION)

        # Test assertions
        self.assertIsNone(entity)

    def _create_alarm_data_composite(self,
                                     state='ok',
                                     type='composite',
                                     rule=None):
        if rule is None:
            rule = {"or":
                    [{"evaluation_periods": 1,
                      "metrics": ["6ade05e5-f98b-4b7d-a0b3-9d330c4c3c41"],
                      "aggregation_method": "mean",
                      "granularity": 60,
                      "threshold": 100.0,
                      "type": "gnocchi_aggregation_by_metrics_threshold",
                      "comparison_operator": "lt"},
                     {"evaluation_periods": 3,
                      "metrics": ["89vde0e5-k3rb-4b7d-a0b3-9d330c4c3c41"],
                      "aggregation_method": "mean",
                      "granularity": 2,
                      "threshold": 80.0,
                      "type": "gnocchi_aggregation_by_metrics_threshold",
                      "comparison_operator": "ge"}
                     ]}
        return {AodhProps.DESCRIPTION: "test",
                AodhProps.TIMESTAMP: "2016-11-09T01:39:13.839584",
                AodhProps.ENABLED: True,
                AodhProps.STATE_TIMESTAMP: "2016-11-09T01:39:13.839584",
                AodhProps.ALARM_ID: "7e5c3754-e2eb-4782-ae00-7da5ded8568b",
                AodhProps.REPEAT_ACTIONS: False,
                AodhProps.PROJECT_ID: "c365d18fcc03493187016ae743f0cc4d",
                AodhProps.NAME: "test",
                AodhProps.SEVERITY: "low",
                AodhProps.RESOURCE_ID: "88cd2d1d-8af4-4d00-9b5e-f82f8c8b0f8d",
                AodhProps.TYPE: type,
                AodhProps.STATE: state,
                AodhProps.RULE: rule}

    def _create_alarm_data_metrics(
            self,
            state='ok',
            type=AType.GNOCCHI_AGGREGATION_BY_METRICS_THRESHOLD,
            rule=None
    ):
        if rule is None:
            rule = {"threshold": '100',
                    "aggregation_method": "mean",
                    "comparison_operator": "lt"
                    }

        return {AodhProps.DESCRIPTION: "metric test",
                AodhProps.TIMESTAMP: "2017-04-03T01:39:13.839584",
                AodhProps.ENABLED: True,
                AodhProps.STATE_TIMESTAMP: "2017-04-03T01:39:13.839584",
                AodhProps.ALARM_ID: "7e5c3754-e2eb-4782-ae00-7da5ded8568b",
                AodhProps.REPEAT_ACTIONS: False,
                AodhProps.PROJECT_ID: "c365d18fcc03493187016ae743f0cc4d",
                AodhProps.NAME: "test",
                AodhProps.SEVERITY: "low",
                AodhProps.RESOURCE_ID: "88cd2d1d-8af4-4d00-9b5e-f82f8c8b0f8d",
                AodhProps.METRICS: "6ade05e5-f98b-4b7d-a0b3-9d330c4c3c41",
                AodhProps.TYPE: type,
                AodhProps.STATE: state,
                AodhProps.RULE: rule}

    def _create_alarm_data_resource(
            self,
            state='ok',
            type=AType.GNOCCHI_AGGREGATION_BY_RESOURCES_THRESHOLD,
            rule=None):
        if rule is None:
            rule = {"evaluation_periods": 3,
                    "metric": "cpu_util",
                    "aggregation_method": "mean",
                    "granularity": 300,
                    "threshold": 50.0,
                    "query": [{"=":
                              {"resource_id":
                               "6df1747a-ef31-4897-854e-ffa2ae568e45"}}],
                    "comparison_operator": "ge",
                    "resource_type": "instance"
                    }

        return {AodhProps.DESCRIPTION: "test",
                AodhProps.TIMESTAMP: "2016-11-09T01:39:13.839584",
                AodhProps.ENABLED: True,
                AodhProps.STATE_TIMESTAMP: "2016-11-09T01:39:13.839584",
                AodhProps.ALARM_ID: "7e5c3754-e2eb-4782-ae00-7da5ded8568b",
                AodhProps.REPEAT_ACTIONS: False,
                AodhProps.PROJECT_ID: "c365d18fcc03493187016ae743f0cc4d",
                AodhProps.NAME: "test",
                AodhProps.SEVERITY: "low",
                AodhProps.RESOURCE_ID: "88cd2d1d-8af4-4d00-9b5e-f82f8c8b0f8d",
                AodhProps.TYPE: type,
                AodhProps.STATE: state,
                AodhProps.RULE: rule}

    def _create_alarm_data_gnocchi(self,
                                   state="ok",
                                   type="gnocchi_resources_threshold",
                                   rule=None):

        if rule is None:
            rule = {"granularity": "300",
                    "threshold": "0.001",
                    "comparison_operator": "gt",
                    "resource_type": "instance",
                    AodhProps.RESOURCE_ID:
                        "88cd2d1d-8af4-4d00-9b5e-f82f8c8b0f8d"
                    }
        return {AodhProps.DESCRIPTION: "test",
                AodhProps.TIMESTAMP: "2016-11-09T01:39:13.839584",
                AodhProps.ENABLED: True,
                AodhProps.STATE_TIMESTAMP: "2016-11-09T01:39:13.839584",
                AodhProps.ALARM_ID: "7e5c3754-e2eb-4782-ae00-7da5ded8568b",
                AodhProps.REPEAT_ACTIONS: False,
                AodhProps.PROJECT_ID: "c365d18fcc03493187016ae743f0cc4d",
                AodhProps.NAME: "test",
                AodhProps.SEVERITY: "low",
                AodhProps.RESOURCE_ID: "88cd2d1d-8af4-4d00-9b5e-f82f8c8b0f8d",
                AodhProps.TYPE: type,
                AodhProps.STATE: state,
                AodhProps.RULE: rule}

    def _create_alarm_data_type_event(self,
                                      state="ok",
                                      type="event",
                                      rule=None):

        if rule is None:
            rule = {"query": [], "event_type": "*"}
        return {AodhProps.DESCRIPTION: "test",
                AodhProps.TIMESTAMP: "2016-11-09T01:39:13.839584",
                AodhProps.ENABLED: True,
                AodhProps.STATE_TIMESTAMP: "2016-11-09T01:39:13.839584",
                AodhProps.ALARM_ID: "7e5c3754-e2eb-4782-ae00-7da5ded8568b",
                AodhProps.REPEAT_ACTIONS: False,
                AodhProps.PROJECT_ID: "c365d18fcc03493187016ae743f0cc4d",
                AodhProps.NAME: "test",
                AodhProps.SEVERITY: "low",
                AodhProps.TYPE: type,
                AodhProps.STATE: state,
                AodhProps.RULE: rule}

    def _validate_aodh_entity_comm_props(self, entity, alarm):

        self.assertEqual(entity[AodhProps.ALARM_ID],
                         alarm[AodhProps.ALARM_ID])
        self.assertEqual(entity[AodhProps.PROJECT_ID],
                         alarm[AodhProps.PROJECT_ID])
        self.assertEqual(entity[AodhProps.TIMESTAMP],
                         alarm[AodhProps.TIMESTAMP])
        self.assertEqual(entity[AodhProps.DESCRIPTION],
                         alarm[AodhProps.DETAIL][AodhProps.DESCRIPTION])
        self.assertEqual(entity[AodhProps.ENABLED],
                         alarm[AodhProps.DETAIL][AodhProps.ENABLED])
        self.assertEqual(entity[AodhProps.NAME],
                         alarm[AodhProps.DETAIL][AodhProps.NAME])
        self.assertEqual(entity[AodhProps.REPEAT_ACTIONS],
                         alarm[AodhProps.DETAIL][AodhProps.REPEAT_ACTIONS])
        self.assertEqual(entity[AodhProps.TYPE],
                         alarm[AodhProps.DETAIL][AodhProps.TYPE])
