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

import queue

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProp
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import TemplateTopologyFields as TTFields
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.alarm_properties import AlarmProperties as AlarmProps
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources.nagios.properties import NagiosProperties as NProps
from vitrage.datasources.nagios.properties import NagiosTestStatus
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.entity_graph.mappings.operational_alarm_severity import \
    OperationalAlarmSeverity
from vitrage.entity_graph.mappings.operational_resource_state import \
    OperationalResourceState
from vitrage.evaluator.actions.action_executor import ActionExecutor
from vitrage.evaluator.actions.base import ActionMode
from vitrage.evaluator.actions.base import ActionType
from vitrage.evaluator.actions.evaluator_event_transformer \
    import VITRAGE_DATASOURCE
from vitrage.evaluator.actions.recipes.action_steps import ADD_VERTEX
from vitrage.evaluator.actions.recipes.base import EVALUATOR_EVENT_TYPE
from vitrage.evaluator.scenario_evaluator import ActionInfo
from vitrage.evaluator.template_data import ActionSpecs
from vitrage.evaluator.template_fields import TemplateFields as TFields
from vitrage.opts import register_opts
from vitrage.tests.functional.base import TestFunctionalBase
from vitrage.tests.functional.test_configuration import TestConfiguration


class TestActionExecutor(TestFunctionalBase, TestConfiguration):

    def setUp(self):
        super(TestActionExecutor, self).setUp()
        self.add_db()

        for datasource_name in self.conf.datasources.types:
            register_opts(datasource_name, self.conf.datasources.path)

    def _init_executer(self):
        event_queue = queue.Queue()

        def actions_callback(event_type, data):
            event_queue.put(data)

        return event_queue, ActionExecutor(actions_callback)

    def test_execute_set_state(self):

        # Test Setup
        processor = self._create_processor_with_graph()

        vertex_attrs = {VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE}
        host_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter=vertex_attrs)
        host_vertex_before = host_vertices[0]

        targets = {TFields.TARGET: host_vertex_before}
        props = {TFields.STATE: OperationalResourceState.SUBOPTIMAL}
        action_spec = ActionSpecs(0, ActionType.SET_STATE, targets, props)

        event_queue, action_executor = self._init_executer()

        # Test Action - do
        action_executor.execute(
            [ActionInfo(action_spec, ActionMode.DO, None, None)])
        self._consume_queue(event_queue, processor)

        host_vertex_after = processor.entity_graph.get_vertex(
            host_vertex_before.vertex_id)

        # Test Assertions
        agg_state_before = \
            host_vertex_before.get(VProps.VITRAGE_AGGREGATED_STATE)
        self.assertNotEqual(agg_state_before,
                            OperationalResourceState.SUBOPTIMAL)
        self.assertNotIn(VProps.VITRAGE_STATE, host_vertex_before.properties)

        agg_state_after = \
            host_vertex_after.get(VProps.VITRAGE_AGGREGATED_STATE)
        self.assertEqual(agg_state_after, OperationalResourceState.SUBOPTIMAL)
        v_state_after = host_vertex_after.get(VProps.VITRAGE_STATE)
        self.assertEqual(v_state_after, OperationalResourceState.SUBOPTIMAL)

        # Test Action - undo
        action_executor.execute(
            [ActionInfo(action_spec, ActionMode.UNDO, None, None)])
        self._consume_queue(event_queue, processor)

        host_vertex_after_undo = processor.entity_graph.get_vertex(
            host_vertex_before.vertex_id)

        # Test Assertions
        agg_state_after_undo = \
            host_vertex_before.get(VProps.VITRAGE_AGGREGATED_STATE)
        self.assertEqual(agg_state_after_undo, agg_state_before)
        self.assertNotIn(
            VProps.VITRAGE_STATE, host_vertex_after_undo.properties)

    def test_execute_mark_instance_down(self):

        # Test Setup
        processor = self._create_processor_with_graph()

        vertex_attrs = {VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE}
        instance_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter=vertex_attrs)
        instance_vertex_before = instance_vertices[0]

        targets = {TFields.TARGET: instance_vertex_before}
        props = {}
        action_spec = ActionSpecs(0, ActionType.MARK_DOWN, targets, props)

        event_queue, action_executor = self._init_executer()

        # Test Action - do
        action_executor.execute(
            [ActionInfo(action_spec, ActionMode.DO, None, None)])
        self._consume_queue(event_queue, processor)

        instance_vertex_after = processor.entity_graph.get_vertex(
            instance_vertex_before.vertex_id)

        # Test Assertions
        self.assertTrue(instance_vertex_after.get(VProps.IS_MARKED_DOWN))

        # Test Action - undo
        action_executor.execute(
            [ActionInfo(action_spec, ActionMode.UNDO, None, None)])
        self._consume_queue(event_queue, processor)

        instance_vertex_after_undo = processor.entity_graph.get_vertex(
            instance_vertex_before.vertex_id)

        # Test Assertions
        self.assertFalse(instance_vertex_after_undo.get(VProps.IS_MARKED_DOWN))

    def test_execute_mark_down(self):

        # Test Setup
        processor = self._create_processor_with_graph()

        vertex_attrs = {VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE}
        host_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter=vertex_attrs)
        host_vertex_before = host_vertices[0]

        targets = {TFields.TARGET: host_vertex_before}
        props = {}
        action_spec = ActionSpecs(0, ActionType.MARK_DOWN, targets, props)

        event_queue, action_executor = self._init_executer()

        # Test Action - do
        action_executor.execute(
            [ActionInfo(action_spec, ActionMode.DO, None, None)])
        self._consume_queue(event_queue, processor)

        host_vertex_after = processor.entity_graph.get_vertex(
            host_vertex_before.vertex_id)

        # Test Assertions
        self.assertTrue(host_vertex_after.get(VProps.IS_MARKED_DOWN))

        # Test Action - undo
        action_executor.execute(
            [ActionInfo(action_spec, ActionMode.UNDO, None, None)])
        self._consume_queue(event_queue, processor)

        host_vertex_after_undo = processor.entity_graph.get_vertex(
            host_vertex_before.vertex_id)

        # Test Assertions
        self.assertFalse(host_vertex_after_undo.get(VProps.IS_MARKED_DOWN))

    def test_execute_add_edge(self):

        # Test Setup
        processor = self._create_processor_with_graph()

        vertex_attrs = {VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE}
        host_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter=vertex_attrs)

        host_1 = host_vertices[0]
        nagios_event1 = TestActionExecutor._get_nagios_event(
            host_1.get(VProps.ID), NOVA_HOST_DATASOURCE)
        processor.process_event(nagios_event1)

        host_2 = host_vertices[1]
        nagios_event2 = TestActionExecutor._get_nagios_event(
            host_2.get(VProps.ID), NOVA_HOST_DATASOURCE)
        processor.process_event(nagios_event2)

        alarms_attrs = {VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE}
        alarms_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter=alarms_attrs)

        alarm1 = alarms_vertices[0]
        alarm2 = alarms_vertices[1]
        targets = {
            TFields.TARGET: alarm1,
            TFields.SOURCE: alarm2
        }
        action_spec = ActionSpecs(
            0, ActionType.ADD_CAUSAL_RELATIONSHIP, targets, {})

        event_queue, action_executor = self._init_executer()

        before_edge = processor.entity_graph.get_edge(alarm2.vertex_id,
                                                      alarm1.vertex_id,
                                                      EdgeLabel.CAUSES)
        # Test Action - do
        action_executor.execute(
            [ActionInfo(action_spec, ActionMode.DO, None, None)])
        self._consume_queue(event_queue, processor)

        new_edge = processor.entity_graph.get_edge(alarm2.vertex_id,
                                                   alarm1.vertex_id,
                                                   EdgeLabel.CAUSES)
        # Test Assertions
        self.assertIsNone(before_edge)
        self.assertIsNotNone(new_edge)

    def test_execute_add_vertex(self):

        # Test Setup
        processor = self._create_processor_with_graph()

        vertex_attrs = {VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE}
        host_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter=vertex_attrs)

        host = host_vertices[0]

        targets = {TFields.TARGET: host}
        props = {
            TFields.ALARM_NAME: 'VM_CPU_SUBOPTIMAL_PERFORMANCE',
            TFields.SEVERITY: OperationalAlarmSeverity.CRITICAL,
            VProps.STATE: AlarmProps.ACTIVE_STATE,
            VProps.RESOURCE_ID: host[VProps.ID],
            VProps.VITRAGE_ID: 'DUMMY_ID'
        }

        # Raise alarm action adds new vertex with type vitrage to the graph
        action_spec = ActionSpecs(0, ActionType.RAISE_ALARM, targets, props)

        alarm_vertex_attrs = {VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE}
        before_alarms = processor.entity_graph.get_vertices(
            vertex_attr_filter=alarm_vertex_attrs)

        event_queue, action_executor = self._init_executer()

        # Test Action
        action_executor.execute(
            [ActionInfo(action_spec, ActionMode.DO, None, None)])
        self._consume_queue(event_queue, processor)

        after_alarms = processor.entity_graph.get_vertices(
            vertex_attr_filter=alarm_vertex_attrs)

        # Assertions
        self.assertEqual(len(before_alarms) + 1, len(after_alarms))
        self.assert_is_not_empty(after_alarms)

        alarm = after_alarms[0]

        self.assertEqual(alarm.properties[VProps.VITRAGE_CATEGORY],
                         EntityCategory.ALARM)
        self.assertEqual(alarm.properties[VProps.VITRAGE_TYPE],
                         VITRAGE_DATASOURCE)
        self.assertEqual(alarm.properties[VProps.SEVERITY],
                         props[TFields.SEVERITY])
        self.assertEqual(alarm.properties[VProps.VITRAGE_OPERATIONAL_SEVERITY],
                         props[TFields.SEVERITY])
        self.assertEqual(alarm.properties[VProps.STATE],
                         AlarmProps.ACTIVE_STATE)
        self.assertEqual(alarm.properties[VProps.VITRAGE_RESOURCE_ID],
                         action_spec.targets
                         [TTFields.TARGET][VProps.VITRAGE_ID]),
        self.assertEqual(alarm.properties[VProps.VITRAGE_RESOURCE_TYPE],
                         NOVA_HOST_DATASOURCE)

    def test_execute_add_and_remove_vertex(self):

        # Test Setup
        processor = self._create_processor_with_graph()

        vertex_attrs = {VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE}
        host_vertices = processor.entity_graph.get_vertices(
            vertex_attr_filter=vertex_attrs)

        host = host_vertices[0]

        targets = {TFields.TARGET: host}
        props = {
            TFields.ALARM_NAME: 'VM_CPU_SUBOPTIMAL_PERFORMANCE',
            TFields.SEVERITY: OperationalAlarmSeverity.CRITICAL,
            VProps.STATE: AlarmProps.ACTIVE_STATE,
            VProps.RESOURCE_ID: host[VProps.ID]
        }
        action_spec = ActionSpecs(0, ActionType.RAISE_ALARM, targets, props)

        add_vertex_event = TestActionExecutor._get_vitrage_add_vertex_event(
            host,
            props[TFields.ALARM_NAME],
            props[TFields.SEVERITY])

        processor.process_event(add_vertex_event)

        alarm_vertex_attrs = {VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                              VProps.VITRAGE_IS_DELETED: False}
        before_alarms = processor.entity_graph.get_vertices(
            vertex_attr_filter=alarm_vertex_attrs)

        event_queue, action_executor = self._init_executer()

        # Test Action - undo
        action_executor.execute(
            [ActionInfo(action_spec, ActionMode.UNDO, None, None)])
        self._consume_queue(event_queue, processor)

        after_alarms = processor.entity_graph.get_vertices(
            vertex_attr_filter=alarm_vertex_attrs)

        # Test Assertions
        self.assertEqual(len(before_alarms) - 1, len(after_alarms))

    @staticmethod
    def _get_nagios_event(resource_name, resource_type):

        return {NProps.LAST_CHECK: '2016-02-07 15:26:04',
                NProps.RESOURCE_NAME: resource_name,
                NProps.RESOURCE_TYPE: resource_type,
                NProps.SERVICE: 'Check_MK',
                NProps.STATUS: NagiosTestStatus.CRITICAL,
                NProps.STATUS_INFO: 'test test test',
                DSProp.DATASOURCE_ACTION: DatasourceAction.SNAPSHOT,
                DSProp.ENTITY_TYPE: NAGIOS_DATASOURCE,
                DSProp.SAMPLE_DATE: '2016-02-07T15:26:04Z'}

    @staticmethod
    def _get_vitrage_add_vertex_event(target_vertex, alarm_name, severity):

        return {TTFields.TARGET: target_vertex.vertex_id,
                VProps.UPDATE_TIMESTAMP: '2016-03-17 11:33:32.443002',
                DSProp.DATASOURCE_ACTION: DatasourceAction.UPDATE,
                TFields.ALARM_NAME: alarm_name,
                VProps.STATE: 'Active',
                EVALUATOR_EVENT_TYPE: ADD_VERTEX,
                DSProp.ENTITY_TYPE: VITRAGE_DATASOURCE,
                VProps.SEVERITY: OperationalAlarmSeverity.CRITICAL,
                VProps.VITRAGE_ID: 'mock_vitrage_id',
                VProps.VITRAGE_RESOURCE_TYPE: NOVA_HOST_DATASOURCE,
                VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                VProps.VITRAGE_SAMPLE_TIMESTAMP:
                    '2016-03-17 11:33:32.443002+00:00'}
