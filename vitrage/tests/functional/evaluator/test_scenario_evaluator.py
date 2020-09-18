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
from oslo_log import log
from testtools import matchers

from vitrage.tests.functional.test_configuration import TestConfiguration

LOG = log.getLogger(__name__)

import queue

from oslo_config import cfg

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EdgeProperties as EProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.cinder.volume.transformer import \
    CINDER_VOLUME_DATASOURCE
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources.nagios.properties import NagiosProperties
from vitrage.datasources.nagios.properties import NagiosTestStatus
from vitrage.datasources.neutron.network import NEUTRON_NETWORK_DATASOURCE
from vitrage.datasources.neutron.port import NEUTRON_PORT_DATASOURCE
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.nova.zone import NOVA_ZONE_DATASOURCE
from vitrage.entity_graph.mappings.operational_resource_state import \
    OperationalResourceState
from vitrage.evaluator.actions.evaluator_event_transformer \
    import VITRAGE_DATASOURCE
from vitrage.evaluator.scenario_evaluator import ScenarioEvaluator
from vitrage.evaluator.scenario_repository import ScenarioRepository
from vitrage.graph import create_edge
from vitrage.tests.base import IsEmpty
from vitrage.tests.functional.base import \
    TestFunctionalBase
import vitrage.tests.mocks.mock_driver as mock_driver
from vitrage.tests.mocks import utils
from vitrage.utils.datetime import utcnow

_TARGET_HOST = 'host-2'
_TARGET_ZONE = 'zone-1'
_NAGIOS_TEST_INFO = {NagiosProperties.RESOURCE_NAME: _TARGET_HOST,
                     'resource_id': _TARGET_HOST,
                     DSProps.DATASOURCE_ACTION: DatasourceAction.SNAPSHOT}


class TestScenarioEvaluator(TestFunctionalBase, TestConfiguration):

    EVALUATOR_OPTS = [
        cfg.StrOpt('templates_dir',
                   default=utils.get_resources_dir() +
                   '/templates/evaluator',
                   ),
        cfg.StrOpt('notifier_topic',
                   default='vitrage.evaluator',
                   ),
    ]

    def setUp(self):
        super(TestScenarioEvaluator, self).setUp()
        self.conf.register_opts(self.EVALUATOR_OPTS, group='evaluator')
        templates_dir = utils.get_resources_dir() + \
            '/templates/evaluator'
        self.add_db()
        self.add_templates(templates_dir)
        self.load_datasources()
        self.scenario_repository = ScenarioRepository()

    def test_deduced_state(self):

        event_queue, processor, evaluator = self._init_system()

        host_v = self._get_entity_from_graph(NOVA_HOST_DATASOURCE,
                                             _TARGET_HOST,
                                             _TARGET_HOST,
                                             processor.entity_graph)
        self.assertEqual('AVAILABLE', host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be AVAILABLE when starting')

        # generate nagios alarm to trigger template scenario
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                     NagiosProperties.SERVICE: 'cause_suboptimal_state'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        warning_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be SUBOPTIMAL with warning alarm')

        # next disable the alarm
        warning_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        self.assertEqual('AVAILABLE', host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be AVAILABLE when alarm disabled')

    def test_overlapping_deduced_state_1(self):

        event_queue, processor, evaluator = self._init_system()

        host_v = self._get_entity_from_graph(NOVA_HOST_DATASOURCE,
                                             _TARGET_HOST,
                                             _TARGET_HOST,
                                             processor.entity_graph)
        self.assertEqual('AVAILABLE', host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be AVAILABLE when starting')

        # generate nagios alarm to trigger
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                     NagiosProperties.SERVICE: 'cause_suboptimal_state'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        warning_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be SUBOPTIMAL with warning alarm')

        # generate CRITICAL nagios alarm to trigger
        test_vals = \
            {NagiosProperties.STATUS: NagiosTestStatus.CRITICAL,
             NagiosProperties.SERVICE: 'cause_error_state'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        critical_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, critical_test,
                                           processor, _TARGET_HOST)
        self.assertEqual(OperationalResourceState.ERROR,
                         host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be ERROR with critical alarm')

        # next disable the critical alarm
        critical_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        host_v = self.get_host_after_event(event_queue, critical_test,
                                           processor, _TARGET_HOST)
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be SUBOPTIMAL with only warning alarm')

        # next disable the alarm
        warning_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        self.assertEqual('AVAILABLE', host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be AVAILABLE after alarm disabled')

    def test_overlapping_deduced_state_2(self):

        event_queue, processor, evaluator = self._init_system()

        host_v = self._get_entity_from_graph(NOVA_HOST_DATASOURCE,
                                             _TARGET_HOST,
                                             _TARGET_HOST,
                                             processor.entity_graph)
        self.assertEqual('AVAILABLE', host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be AVAILABLE when starting')

        # generate CRITICAL nagios alarm to trigger
        test_vals = \
            {NagiosProperties.STATUS: NagiosTestStatus.CRITICAL,
             NagiosProperties.SERVICE: 'cause_error_state'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        critical_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, critical_test,
                                           processor, _TARGET_HOST)
        self.assertEqual(OperationalResourceState.ERROR,
                         host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be ERROR with critical alarm')

        # generate WARNING nagios alarm to trigger
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                     NagiosProperties.SERVICE: 'cause_suboptimal_state'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        warning_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        self.assertEqual(OperationalResourceState.ERROR,
                         host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be ERROR with critical alarm')

        # next disable the critical alarm
        critical_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        host_v = self.get_host_after_event(event_queue, critical_test,
                                           processor, _TARGET_HOST)
        self.assertEqual(OperationalResourceState.SUBOPTIMAL,
                         host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be SUBOPTIMAL with only warning alarm')

    def test_deduced_alarm(self):

        event_queue, processor, evaluator = self._init_system()

        host_v = self._get_entity_from_graph(NOVA_HOST_DATASOURCE,
                                             _TARGET_HOST,
                                             _TARGET_HOST,
                                             processor.entity_graph)
        self.assertEqual('AVAILABLE', host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be AVAILABLE when starting')

        # generate CRITICAL nagios alarm to trigger
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                     NagiosProperties.SERVICE: 'cause_warning_deduced_alarm'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        warning_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(1))
        self.assertEqual(NagiosTestStatus.WARNING,
                         alarms[0][VProps.SEVERITY])
        causes = self._get_alarm_causes(alarms[0], processor.entity_graph)
        self.assertThat(causes, matchers.HasLength(1))

        # next disable the alarm
        warning_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, IsEmpty())

        # recreate the nagios alarm
        warning_test[NagiosProperties.STATUS] = NagiosTestStatus.WARNING
        warning_test[DSProps.SAMPLE_DATE] = str(utcnow())
        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(1))
        self.assertEqual(NagiosTestStatus.WARNING,
                         alarms[0][VProps.SEVERITY])
        causes = self._get_alarm_causes(alarms[0], processor.entity_graph)
        self.assertThat(causes, matchers.HasLength(1))

        # next disable the alarm
        warning_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, IsEmpty())

    def test_overlapping_deduced_alarm_1(self):

        event_queue, processor, evaluator = self._init_system()

        # generate WARNING nagios alarm
        vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                NagiosProperties.SERVICE: 'cause_warning_deduced_alarm'}
        vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, vals)
        warning_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(1))
        self.assertEqual(NagiosTestStatus.WARNING,
                         alarms[0][VProps.SEVERITY])
        causes = self._get_alarm_causes(alarms[0], processor.entity_graph)
        self.assertThat(causes, matchers.HasLength(1))

        # generate CRITICAL nagios alarm to trigger
        vals = {NagiosProperties.STATUS: NagiosTestStatus.CRITICAL,
                NagiosProperties.SERVICE: 'cause_critical_deduced_alarm'}
        vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, vals)
        critical_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, critical_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(1))
        self.assertEqual(NagiosTestStatus.CRITICAL,
                         alarms[0][VProps.SEVERITY])
        causes = self._get_alarm_causes(alarms[0], processor.entity_graph)
        self.assertThat(causes, matchers.HasLength(2))

        # remove WARNING nagios alarm, leaving only CRITICAL one
        warning_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(1))
        self.assertEqual(NagiosTestStatus.CRITICAL, alarms[0][VProps.SEVERITY])
        causes = self._get_alarm_causes(alarms[0], processor.entity_graph)
        self.assertThat(causes, matchers.HasLength(1))

        # next disable the alarm
        critical_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        host_v = self.get_host_after_event(event_queue, critical_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, IsEmpty())

    def test_overlapping_deduced_alarm_2(self):

        event_queue, processor, evaluator = self._init_system()

        # generate CRITICAL nagios alarm to trigger
        test_vals = \
            {NagiosProperties.STATUS: NagiosTestStatus.CRITICAL,
             NagiosProperties.SERVICE: 'cause_critical_deduced_alarm'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        critical_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, critical_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(1))
        self.assertEqual(NagiosTestStatus.CRITICAL,
                         alarms[0][VProps.SEVERITY])

        # generate WARNING nagios alarm to trigger
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                     NagiosProperties.SERVICE: 'cause_warning_deduced_alarm'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        warning_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, warning_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(1))
        self.assertEqual(NagiosTestStatus.CRITICAL,
                         alarms[0][VProps.SEVERITY])

        # remove CRITICAL nagios alarm, leaving only WARNING one
        critical_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        host_v = self.get_host_after_event(event_queue, critical_test,
                                           processor, _TARGET_HOST)
        alarms = \
            self._get_deduced_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(1))
        self.assertEqual(NagiosTestStatus.WARNING,
                         alarms[0][VProps.SEVERITY])

    def test_simple_not_operator_deduced_alarm(self):
        """Handles a simple not operator use case

        We have created the following template: if there is a neutron.port that
        doesn't have a nagios alarm of vitrage_type PORT_PROBLEM on it, then
        raise a deduced alarm on the port called simple_port_deduced_alarm.
        The test has 5 steps in it:
        1. create neutron.network and neutron.port and check that the
           simple_port_deduced_alarm is raised on the neutron.port because it
           doesn't have a nagios alarm on it.
        2. create a nagios alarm called PORT_PROBLEM on the port and check
           that the alarm simple_port_deduced_alarm doesn't appear on the
           neutron.port.
        3. delete the edge between nagios alarm called PORT_PROBLEM and the
           neutron.port. check that the alarm simple_port_deduced_alarm appear
           on the neutron.port.
        4. create the edge between nagios alarm called PORT_PROBLEM and the
           neutron.port.check that the alarm simple_port_deduced_alarm doesn't
           appear on the neutron.port.
        5. delete the nagios alarm called PORT_PROBLEM from the port, and
           check that the alarm alarm simple_port_deduced_alarm appear on the
           neutron.port.
        """

        event_queue, processor, evaluator = self._init_system()
        entity_graph = processor.entity_graph

        # constants
        num_orig_vertices = entity_graph.num_vertices()
        num_orig_edges = entity_graph.num_edges()
        num_added_vertices = 2
        num_added_edges = 2
        num_deduced_vertices = 1
        num_deduced_edges = 1
        num_nagios_alarm_vertices = 1
        num_nagios_alarm_edges = 1

        # find instances
        query = {
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE
        }
        instance_ver = entity_graph.get_vertices(vertex_attr_filter=query)[0]

        # update network
        network_event = {
            'tenant_id': 'admin',
            'name': 'net-0',
            'updated_at': '2015-12-01T12:46:41Z',
            'status': 'active',
            'id': '12345',
            DSProps.ENTITY_TYPE: NEUTRON_NETWORK_DATASOURCE,
            DSProps.DATASOURCE_ACTION: DatasourceAction.SNAPSHOT,
            DSProps.SAMPLE_DATE: '2015-12-01T12:46:41Z',
        }

        # update port
        port_event = {
            'tenant_id': 'admin',
            'name': 'port-0',
            'updated_at': '2015-12-01T12:46:41Z',
            'status': 'active',
            'id': '54321',
            DSProps.ENTITY_TYPE: NEUTRON_PORT_DATASOURCE,
            DSProps.DATASOURCE_ACTION: DatasourceAction.SNAPSHOT,
            DSProps.SAMPLE_DATE: '2015-12-01T12:46:41Z',
            'network_id': '12345',
            'device_id': instance_ver.get(VProps.ID),
            'device_owner': 'compute:nova',
            'fixed_ips': {}
        }

        processor.process_event(network_event)
        processor.process_event(port_event)
        port_vertex = entity_graph.get_vertices(
            vertex_attr_filter={VProps.VITRAGE_TYPE:
                                NEUTRON_PORT_DATASOURCE})[0]
        self._consume_queue(event_queue, processor)

        # test asserts
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM}
        port_neighbors = entity_graph.neighbors(port_vertex.vertex_id,
                                                vertex_attr_filter=query)
        self.assertEqual(num_orig_vertices + num_added_vertices +
                         num_deduced_vertices, entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_added_edges + num_deduced_edges,
                         entity_graph.num_edges())
        self.assertThat(port_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         port_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         port_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('simple_port_deduced_alarm',
                         port_neighbors[0][VProps.NAME])

        # Add PORT_PROBLEM alarm
        test_vals = {'status': NagiosTestStatus.WARNING,
                     'service': 'PORT_PROBLEM',
                     'name': 'PORT_PROBLEM',
                     DSProps.DATASOURCE_ACTION: DatasourceAction.SNAPSHOT,
                     VProps.RESOURCE_ID: port_vertex.get(VProps.ID),
                     NagiosProperties.RESOURCE_NAME:
                         port_vertex.get(VProps.ID),
                     NagiosProperties.RESOURCE_TYPE: NEUTRON_PORT_DATASOURCE}
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        nagios_event = mock_driver.generate_random_events_list(generator)[0]

        processor.process_event(nagios_event)
        self._consume_queue(event_queue, processor)

        # test asserts
        self.assertEqual(num_orig_vertices + num_added_vertices +
                         num_deduced_vertices + num_nagios_alarm_vertices,
                         entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_added_edges + num_deduced_edges +
                         num_nagios_alarm_edges, entity_graph.num_edges())

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE}
        port_neighbors = entity_graph.neighbors(port_vertex.vertex_id,
                                                vertex_attr_filter=query)
        self.assertThat(port_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         port_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         port_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('simple_port_deduced_alarm',
                         port_neighbors[0][VProps.NAME])
        self.assertTrue(port_neighbors[0][VProps.VITRAGE_IS_DELETED])

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE}
        port_neighbors = entity_graph.neighbors(port_vertex.vertex_id,
                                                vertex_attr_filter=query)
        self.assertEqual(EntityCategory.ALARM,
                         port_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(NAGIOS_DATASOURCE,
                         port_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('PORT_PROBLEM', port_neighbors[0][VProps.NAME])
        self.assertFalse(port_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(port_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # ###################   STEP 3   ###################
        # disable connection between port and alarm
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE}
        nagios_vertex = \
            processor.entity_graph.get_vertices(vertex_attr_filter=query)[0]
        nagios_edge = [e for e in processor.entity_graph.get_edges(
            nagios_vertex.vertex_id)][0]
        nagios_edge[EProps.VITRAGE_IS_DELETED] = True
        processor.entity_graph.update_edge(nagios_edge)
        self._consume_queue(event_queue, processor)

        # test asserts
        self.assertEqual(num_orig_vertices + num_added_vertices +
                         num_deduced_vertices + num_nagios_alarm_vertices +
                         # a new uuid is created for every new vertex,
                         # even if it existed before with another uuid.
                         # new alarm doesn't override old one
                         1,
                         entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_added_edges + num_deduced_edges +
                         num_nagios_alarm_edges + 1, entity_graph.num_edges())

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                 VProps.VITRAGE_IS_DELETED: True}
        vitrage_is_deleted = True
        for counter in range(0, 1):
            port_neighbors = entity_graph.neighbors(port_vertex.vertex_id,
                                                    vertex_attr_filter=query)
            self.assertThat(port_neighbors, matchers.HasLength(1))
            self.assertEqual(port_neighbors[0][VProps.VITRAGE_CATEGORY],
                             EntityCategory.ALARM)
            self.assertEqual(port_neighbors[0][VProps.VITRAGE_TYPE],
                             VITRAGE_DATASOURCE)
            self.assertEqual(port_neighbors[0][VProps.NAME],
                             'simple_port_deduced_alarm')
            self.assertEqual(port_neighbors[0][VProps.VITRAGE_IS_DELETED],
                             vitrage_is_deleted)
            query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                     VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                     VProps.VITRAGE_IS_DELETED: False}
            vitrage_is_deleted = False

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE}
        port_neighbors = entity_graph.neighbors(port_vertex.vertex_id,
                                                vertex_attr_filter=query)
        self.assertEqual(EntityCategory.ALARM,
                         port_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(NAGIOS_DATASOURCE,
                         port_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('PORT_PROBLEM', port_neighbors[0][VProps.NAME])
        self.assertFalse(port_neighbors[0][VProps.VITRAGE_IS_DELETED])

        # ###################   STEP 4   ###################
        # enable connection between port and alarm
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE}
        nagios_vertex = \
            processor.entity_graph.get_vertices(vertex_attr_filter=query)[0]
        nagios_edge = [e for e in processor.entity_graph.get_edges(
            nagios_vertex.vertex_id)][0]
        nagios_edge[EProps.VITRAGE_IS_DELETED] = False
        processor.entity_graph.update_edge(nagios_edge)
        self._consume_queue(event_queue, processor)

        # test asserts
        self.assertEqual(num_orig_vertices + num_added_vertices +
                         num_deduced_vertices + num_nagios_alarm_vertices +
                         # a new uuid is created for every new vertex,
                         # even if it existed before with another uuid.
                         # new alarm doesn't override old one
                         1,
                         entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_added_edges + num_deduced_edges +
                         num_nagios_alarm_edges + 1, entity_graph.num_edges())

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                 VProps.VITRAGE_IS_DELETED: True}
        vitrage_is_deleted = True
        for counter in range(0, 1):
            port_neighbors = entity_graph.neighbors(port_vertex.vertex_id,
                                                    vertex_attr_filter=query)
            self.assertThat(port_neighbors, matchers.HasLength(2))
            for in_counter in range(0, 1):
                self.assertEqual(
                    EntityCategory.ALARM,
                    port_neighbors[in_counter][VProps.VITRAGE_CATEGORY])
                self.assertEqual(VITRAGE_DATASOURCE,
                                 port_neighbors[in_counter]
                                 [VProps.VITRAGE_TYPE])
                self.assertEqual('simple_port_deduced_alarm',
                                 port_neighbors[in_counter][VProps.NAME])
                self.assertEqual(
                    vitrage_is_deleted,
                    port_neighbors[in_counter][VProps.VITRAGE_IS_DELETED])

            query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                     VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                     VProps.VITRAGE_IS_DELETED: False}
            vitrage_is_deleted = False

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE}
        port_neighbors = entity_graph.neighbors(port_vertex.vertex_id,
                                                vertex_attr_filter=query)
        self.assertEqual(EntityCategory.ALARM,
                         port_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(NAGIOS_DATASOURCE,
                         port_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('PORT_PROBLEM', port_neighbors[0][VProps.NAME])
        self.assertFalse(port_neighbors[0][VProps.VITRAGE_IS_DELETED])

        # ###################   STEP 5   ###################
        # disable PORT_PROBLEM alarm
        nagios_event[NagiosProperties.STATUS] = NagiosTestStatus.OK
        processor.process_event(nagios_event)
        self._consume_queue(event_queue, processor)

        # test asserts
        self.assertEqual(num_orig_vertices + num_added_vertices +
                         num_deduced_vertices + num_nagios_alarm_vertices +
                         # a new uuid is created for every new vertex,
                         # even if it existed before with another uuid.
                         # new alarm doesn't override old one
                         2,
                         entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_added_edges + num_deduced_edges +
                         num_nagios_alarm_edges + 2, entity_graph.num_edges())

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                 VProps.VITRAGE_IS_DELETED: True}
        vitrage_is_deleted = True
        for counter in range(0, 1):
            port_neighbors = entity_graph.neighbors(port_vertex.vertex_id,
                                                    vertex_attr_filter=query)
            self.assertThat(port_neighbors, matchers.HasLength(2))
            for in_counter in range(0, 1):
                self.assertEqual(
                    EntityCategory.ALARM,
                    port_neighbors[in_counter][VProps.VITRAGE_CATEGORY])
                self.assertEqual(VITRAGE_DATASOURCE,
                                 port_neighbors[in_counter]
                                 [VProps.VITRAGE_TYPE])
                self.assertEqual('simple_port_deduced_alarm',
                                 port_neighbors[in_counter][VProps.NAME])
                self.assertEqual(
                    vitrage_is_deleted,
                    port_neighbors[in_counter][VProps.VITRAGE_IS_DELETED])

            query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                     VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                     VProps.VITRAGE_IS_DELETED: False}
            vitrage_is_deleted = False

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE}
        port_neighbors = entity_graph.neighbors(port_vertex.vertex_id,
                                                vertex_attr_filter=query)
        self.assertEqual(EntityCategory.ALARM,
                         port_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(NAGIOS_DATASOURCE,
                         port_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('PORT_PROBLEM', port_neighbors[0][VProps.NAME])
        self.assertTrue(port_neighbors[0][VProps.VITRAGE_IS_DELETED])

    def test_complex_not_operator_deduced_alarm(self):
        """Handles a complex not operator use case

        We have created the following template: if there is an
        openstack.cluster that has a nova.zone which is connected to a
        neutron.network and also there is no nagios alarm of vitrage_type
        CLUSTER_PROBLEM on the cluster and no nagios alarm of vitrage_type
        NETWORK_PROBLEM on the neutron.network, then raise a deduced alarm
        on the nova.zone called complex_zone_deduced_alarm.
        The test has 3 steps in it:
        1. create a neutron.network and connect it to a zone, and check that
           the complex_zone_deduced_alarm is raised on the nova.zone because it
           doesn't have nagios alarms the openstack.cluster and on the
           neutron.network.
        2. create a nagios alarm called NETWORK_PROBLEM on the network and
           check that the alarm complex_zone_deduced_alarm doesn't appear on
           the nova.zone.
        3. delete the nagios alarm called NETWORK_PROBLEM from the port, and
           check that the alarm alarm complex_zone_deduced_alarm appear on the
           nova.zone.
        """

        event_queue, processor, evaluator = self._init_system()
        entity_graph = processor.entity_graph

        # constants
        num_orig_vertices = entity_graph.num_vertices()
        num_orig_edges = entity_graph.num_edges()
        num_added_vertices = 2
        num_added_edges = 3
        num_deduced_vertices = 1
        num_deduced_edges = 1
        num_network_alarm_vertices = 1
        num_network_alarm_edges = 1

        # ###################   STEP 1   ###################
        # update zone
        generator = mock_driver.simple_zone_generators(1, 1, snapshot_events=1)
        zone_event = mock_driver.generate_random_events_list(generator)[0]
        zone_event['zoneName'] = 'zone-7'

        # update network
        network_event = {
            'tenant_id': 'admin',
            'name': 'net-0',
            'updated_at': '2015-12-01T12:46:41Z',
            'status': 'active',
            'id': '12345',
            DSProps.ENTITY_TYPE: NEUTRON_NETWORK_DATASOURCE,
            DSProps.DATASOURCE_ACTION: DatasourceAction.SNAPSHOT,
            DSProps.SAMPLE_DATE: '2015-12-01T12:46:41Z',
        }

        # process events
        processor.process_event(zone_event)
        query = {VProps.VITRAGE_TYPE: NOVA_ZONE_DATASOURCE,
                 VProps.ID: 'zone-7'}
        zone_vertex = entity_graph.get_vertices(vertex_attr_filter=query)[0]
        processor.process_event(network_event)
        query = {VProps.VITRAGE_TYPE: NEUTRON_NETWORK_DATASOURCE}
        network_vertex = entity_graph.get_vertices(vertex_attr_filter=query)[0]

        # add edge between network and zone
        edge = create_edge(network_vertex.vertex_id, zone_vertex.vertex_id,
                           EdgeLabel.ATTACHED)
        entity_graph.add_edge(edge)

        self._consume_queue(event_queue, processor)

        # test asserts
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM}
        zone_neighbors = entity_graph.neighbors(zone_vertex.vertex_id,
                                                vertex_attr_filter=query)
        self.assertEqual(num_orig_vertices + num_added_vertices +
                         num_deduced_vertices, entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_added_edges + num_deduced_edges,
                         entity_graph.num_edges())
        self.assertThat(zone_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         zone_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         zone_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('complex_zone_deduced_alarm',
                         zone_neighbors[0][VProps.NAME])

        # ###################   STEP 2   ###################
        # Add NETWORK_PROBLEM alarm
        test_vals = {'status': NagiosTestStatus.WARNING,
                     'service': 'NETWORK_PROBLEM',
                     'name': 'NETWORK_PROBLEM',
                     DSProps.DATASOURCE_ACTION: DatasourceAction.SNAPSHOT,
                     VProps.RESOURCE_ID: network_vertex[VProps.ID],
                     NagiosProperties.RESOURCE_NAME: network_vertex[VProps.ID],
                     NagiosProperties.RESOURCE_TYPE:
                         NEUTRON_NETWORK_DATASOURCE}
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        nagios_event = mock_driver.generate_random_events_list(generator)[0]

        processor.process_event(nagios_event)
        self._consume_queue(event_queue, processor)

        self.assertEqual(num_orig_vertices + num_added_vertices +
                         num_deduced_vertices + num_network_alarm_vertices,
                         entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_added_edges + num_deduced_edges +
                         num_network_alarm_edges, entity_graph.num_edges())

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM}
        network_neighbors = entity_graph.neighbors(network_vertex.vertex_id,
                                                   vertex_attr_filter=query)
        self.assertThat(network_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         network_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(NAGIOS_DATASOURCE,
                         network_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('NETWORK_PROBLEM', network_neighbors[0][VProps.NAME])
        self.assertFalse(network_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(network_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        zone_neighbors = entity_graph.neighbors(zone_vertex.vertex_id,
                                                vertex_attr_filter=query)
        self.assertThat(zone_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         zone_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         zone_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('complex_zone_deduced_alarm',
                         zone_neighbors[0][VProps.NAME])
        self.assertTrue(zone_neighbors[0][VProps.VITRAGE_IS_DELETED])

        # ###################   STEP 3   ###################
        # delete NETWORK_PROBLEM alarm
        nagios_event[NagiosProperties.STATUS] = NagiosTestStatus.OK
        processor.process_event(nagios_event)
        self._consume_queue(event_queue, processor)

        self.assertEqual(num_orig_vertices + num_added_vertices +
                         num_deduced_vertices + num_network_alarm_vertices +
                         # a new uuid is created for every new vertex,
                         # even if it existed before with another uuid.
                         # new alarm doesn't override old one
                         1,
                         entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_added_edges + num_deduced_edges +
                         num_network_alarm_edges + 1, entity_graph.num_edges())

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM}
        network_neighbors = entity_graph.neighbors(network_vertex.vertex_id,
                                                   vertex_attr_filter=query)
        self.assertThat(network_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         network_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(NAGIOS_DATASOURCE,
                         network_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('NETWORK_PROBLEM', network_neighbors[0][VProps.NAME])
        self.assertTrue(network_neighbors[0][VProps.VITRAGE_IS_DELETED])

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_IS_DELETED: True}
        vitrage_is_deleted = True
        # Alarm History is saved. We are testing the deleted alarm and
        # then we are testing the live alarm
        for counter in range(0, 1):
            zone_neighbors = entity_graph.neighbors(zone_vertex.vertex_id,
                                                    vertex_attr_filter=query)
            self.assertThat(zone_neighbors, matchers.HasLength(1))
            self.assertEqual(EntityCategory.ALARM,
                             zone_neighbors[0][VProps.VITRAGE_CATEGORY])
            self.assertEqual(VITRAGE_DATASOURCE,
                             zone_neighbors[0][VProps.VITRAGE_TYPE])
            self.assertEqual('complex_zone_deduced_alarm',
                             zone_neighbors[0][VProps.NAME])
            self.assertEqual(vitrage_is_deleted,
                             zone_neighbors[0][VProps.VITRAGE_IS_DELETED])

            query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                     VProps.VITRAGE_IS_DELETED: False}
            vitrage_is_deleted = False

    def test_ha(self):
        event_queue, processor, evaluator = self._init_system()
        entity_graph = processor.entity_graph

        # find host
        query = {
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE
        }
        hosts = entity_graph.get_vertices(vertex_attr_filter=query)

        # find instances on host
        query = {
            VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
            VProps.VITRAGE_TYPE: NOVA_INSTANCE_DATASOURCE
        }
        instances = entity_graph.neighbors(hosts[0].vertex_id,
                                           vertex_attr_filter=query)
        entity_graph.remove_vertex(instances[2])
        entity_graph.remove_vertex(instances[3])

        # constants
        num_orig_vertices = entity_graph.num_vertices()
        num_orig_edges = entity_graph.num_edges()

        # ###################   STEP 1   ###################
        # Add cinder volume 1
        generator = mock_driver.simple_volume_generators(volume_num=1,
                                                         instance_num=1,
                                                         snapshot_events=1)
        volume_event1 = mock_driver.generate_random_events_list(generator)[0]
        volume_event1['display_name'] = 'volume-1'
        volume_event1[VProps.ID] = 'volume-1'
        volume_event1['attachments'][0]['server_id'] = instances[0][VProps.ID]

        processor.process_event(volume_event1)
        self._consume_queue(event_queue, processor)

        # test asserts
        num_volumes = 1
        num_deduced_alarms = 1
        self.assertEqual(num_orig_vertices + num_volumes + num_deduced_alarms,
                         entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_volumes + num_deduced_alarms,
                         entity_graph.num_edges())

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                 VProps.VITRAGE_TYPE: CINDER_VOLUME_DATASOURCE}
        instance_neighbors = entity_graph.neighbors(instances[0].vertex_id,
                                                    vertex_attr_filter=query)
        self.assertThat(instance_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.RESOURCE,
                         instance_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(CINDER_VOLUME_DATASOURCE,
                         instance_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('volume-1', instance_neighbors[0][VProps.NAME])
        self.assertFalse(instance_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(instance_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE}
        host_neighbors = entity_graph.neighbors(hosts[0].vertex_id,
                                                vertex_attr_filter=query)
        self.assertEqual(EntityCategory.ALARM,
                         host_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         host_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('ha_warning_deduced_alarm',
                         host_neighbors[0][VProps.NAME])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # ###################   STEP 2   ###################
        # Add cinder volume 2
        generator = mock_driver.simple_volume_generators(volume_num=1,
                                                         instance_num=1,
                                                         snapshot_events=1)
        volume_event2 = mock_driver.generate_random_events_list(generator)[0]
        volume_event2['display_name'] = 'volume-2'
        volume_event2[VProps.ID] = 'volume-2'
        volume_event2['attachments'][0]['server_id'] = instances[1][VProps.ID]

        processor.process_event(volume_event2)
        self._consume_queue(event_queue, processor)

        # test asserts
        num_volumes = 2
        num_deduced_alarms = 2
        self.assertEqual(num_orig_vertices + num_volumes + num_deduced_alarms,
                         entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_volumes + num_deduced_alarms,
                         entity_graph.num_edges())

        # check instance neighbors
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                 VProps.VITRAGE_TYPE: CINDER_VOLUME_DATASOURCE}
        instance_neighbors = entity_graph.neighbors(instances[1].vertex_id,
                                                    vertex_attr_filter=query)
        self.assertThat(instance_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.RESOURCE,
                         instance_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(CINDER_VOLUME_DATASOURCE,
                         instance_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('volume-2', instance_neighbors[0][VProps.NAME])
        self.assertFalse(instance_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(instance_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # check ha_error_deduced_alarm
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                 VProps.NAME: 'ha_error_deduced_alarm'}
        host_neighbors = entity_graph.neighbors(hosts[0].vertex_id,
                                                vertex_attr_filter=query)
        self.assertThat(host_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         host_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         host_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('ha_error_deduced_alarm',
                         host_neighbors[0][VProps.NAME])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # check ha_warning_deduced_alarm
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                 VProps.NAME: 'ha_warning_deduced_alarm'}
        host_neighbors = entity_graph.neighbors(hosts[0].vertex_id,
                                                vertex_attr_filter=query)
        self.assertThat(host_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         host_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         host_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('ha_warning_deduced_alarm',
                         host_neighbors[0][VProps.NAME])
        self.assertTrue(host_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # ###################   STEP 3   ###################
        #  Remove Cinder Volume 2
        volume_event2[DSProps.DATASOURCE_ACTION] = DatasourceAction.UPDATE
        volume_event2[DSProps.EVENT_TYPE] = 'volume.detach.start'
        volume_event2['volume_id'] = volume_event2['id']
        volume_event2['volume_attachment'] = volume_event2['attachments']
        volume_event2['volume_attachment'][0]['instance_uuid'] = \
            volume_event2['attachments'][0]['server_id']
        processor.process_event(volume_event2)
        self._consume_queue(event_queue, processor)

        # test asserts
        self.assertEqual(num_orig_vertices + num_volumes + num_deduced_alarms +
                         # a new uuid is created for every new vertex,
                         # even if it existed before with another uuid.
                         # new alarm doesn't override old one
                         1,
                         entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_volumes + num_deduced_alarms + 1,
                         entity_graph.num_edges())

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                 VProps.VITRAGE_TYPE: CINDER_VOLUME_DATASOURCE}
        instance_neighbors = entity_graph.neighbors(instances[1].vertex_id,
                                                    vertex_attr_filter=query)
        self.assertThat(instance_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.RESOURCE,
                         instance_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(CINDER_VOLUME_DATASOURCE,
                         instance_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('volume-2', instance_neighbors[0][VProps.NAME])
        self.assertFalse(instance_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(instance_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # check ha_error_deduced_alarm
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                 VProps.NAME: 'ha_error_deduced_alarm'}
        host_neighbors = entity_graph.neighbors(hosts[0].vertex_id,
                                                vertex_attr_filter=query)
        self.assertThat(host_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         host_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         host_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('ha_error_deduced_alarm',
                         host_neighbors[0][VProps.NAME])
        self.assertTrue(host_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # check new ha_warning_deduced_alarm
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                 VProps.NAME: 'ha_warning_deduced_alarm',
                 VProps.VITRAGE_IS_DELETED: False}
        host_neighbors = entity_graph.neighbors(hosts[0].vertex_id,
                                                vertex_attr_filter=query)
        self.assertThat(host_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         host_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         host_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('ha_warning_deduced_alarm',
                         host_neighbors[0][VProps.NAME])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # check old deleted ha_warning_deduced_alarm
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                 VProps.NAME: 'ha_warning_deduced_alarm',
                 VProps.VITRAGE_IS_DELETED: True}
        host_neighbors = entity_graph.neighbors(hosts[0].vertex_id,
                                                vertex_attr_filter=query)
        self.assertThat(host_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         host_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         host_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('ha_warning_deduced_alarm',
                         host_neighbors[0][VProps.NAME])
        self.assertTrue(host_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # ###################   STEP 4   ###################
        #  Remove Cinder Volume 1
        volume_event1[DSProps.DATASOURCE_ACTION] = DatasourceAction.UPDATE
        volume_event1[DSProps.EVENT_TYPE] = 'volume.detach.start'
        volume_event1['volume_id'] = volume_event1['id']
        volume_event1['volume_attachment'] = volume_event1['attachments']
        volume_event1['volume_attachment'][0]['instance_uuid'] = \
            volume_event1['attachments'][0]['server_id']
        processor.process_event(volume_event1)
        self._consume_queue(event_queue, processor)

        # test asserts
        self.assertEqual(num_orig_vertices + num_volumes + num_deduced_alarms +
                         # a new uuid is created for every new vertex,
                         # even if it existed before with another uuid.
                         # new alarm doesn't override old one
                         1,
                         entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + num_volumes + num_deduced_alarms + 1,
                         entity_graph.num_edges())

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                 VProps.VITRAGE_TYPE: CINDER_VOLUME_DATASOURCE}
        instance_neighbors = entity_graph.neighbors(instances[0].vertex_id,
                                                    vertex_attr_filter=query)
        self.assertThat(instance_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.RESOURCE,
                         instance_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(CINDER_VOLUME_DATASOURCE,
                         instance_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('volume-1', instance_neighbors[0][VProps.NAME])
        self.assertFalse(instance_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(instance_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # check ha_error_deduced_alarm
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                 VProps.NAME: 'ha_error_deduced_alarm'}
        host_neighbors = entity_graph.neighbors(hosts[0].vertex_id,
                                                vertex_attr_filter=query)
        self.assertThat(host_neighbors, matchers.HasLength(1))
        self.assertEqual(EntityCategory.ALARM,
                         host_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         host_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('ha_error_deduced_alarm',
                         host_neighbors[0][VProps.NAME])
        self.assertTrue(host_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        # check old ha_warning_deduced_alarm
        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                 VProps.NAME: 'ha_warning_deduced_alarm'}
        host_neighbors = entity_graph.neighbors(hosts[0].vertex_id,
                                                vertex_attr_filter=query)
        self.assertThat(host_neighbors, matchers.HasLength(2))

        self.assertEqual(EntityCategory.ALARM,
                         host_neighbors[0][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         host_neighbors[0][VProps.VITRAGE_TYPE])
        self.assertEqual('ha_warning_deduced_alarm',
                         host_neighbors[0][VProps.NAME])
        self.assertTrue(host_neighbors[0][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(host_neighbors[0][VProps.VITRAGE_IS_PLACEHOLDER])

        self.assertEqual(EntityCategory.ALARM,
                         host_neighbors[1][VProps.VITRAGE_CATEGORY])
        self.assertEqual(VITRAGE_DATASOURCE,
                         host_neighbors[1][VProps.VITRAGE_TYPE])
        self.assertEqual('ha_warning_deduced_alarm',
                         host_neighbors[1][VProps.NAME])
        self.assertTrue(host_neighbors[1][VProps.VITRAGE_IS_DELETED])
        self.assertFalse(host_neighbors[1][VProps.VITRAGE_IS_PLACEHOLDER])

    def test_simple_or_operator_deduced_alarm(self):
        """Handles a simple not operator use case

        We have created the following template:
        alarm1 or alarm2 cause alarm3

        """

        event_queue, processor, evaluator = self._init_system()

        host_v = self._get_entity_from_graph(NOVA_HOST_DATASOURCE,
                                             _TARGET_HOST,
                                             _TARGET_HOST,
                                             processor.entity_graph)
        self.assertEqual('AVAILABLE', host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be AVAILABLE when starting')

        # generate nagios alarm1 to trigger, raise alarm3
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                     NagiosProperties.SERVICE: 'alarm1'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        alarm1_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, alarm1_test,
                                           processor, _TARGET_HOST)
        alarms = self._get_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(2))

        # generate nagios alarm2 to trigger
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                     NagiosProperties.SERVICE: 'alarm2'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        alarm2_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, alarm2_test,
                                           processor, _TARGET_HOST)
        alarms = self._get_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(3))
        # disable alarm1, alarm3 is not deleted
        alarm1_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        host_v = self.get_host_after_event(event_queue, alarm1_test,
                                           processor, _TARGET_HOST)
        alarms = self._get_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, matchers.HasLength(2))

        # disable alarm2, alarm3 is deleted
        alarm2_test[NagiosProperties.STATUS] = NagiosTestStatus.OK
        alarm2_test[DSProps.SAMPLE_DATE] = str(utcnow())
        host_v = self.get_host_after_event(event_queue, alarm2_test,
                                           processor, _TARGET_HOST)
        alarms = self._get_alarms_on_host(host_v, processor.entity_graph)
        self.assertThat(alarms, IsEmpty())

    def test_both_and_or_operator_for_tracker(self):
        """(alarm_a or alarm_b) and alarm_c use case

        We have created the following template:
        (alarm_a or alarm_b) and alarm_c cause alarm_d

        1. alarm_a is reported
        2. alarm_b is reported
        3. alarm_c is reported  --> alarm_d is raised
        4. alarm_b is removed   --> alarm_d should not be removed
        5. alarm_a is removed   --> alarm_d should be removed

        """

        event_queue, processor, evaluator = self._init_system()
        entity_graph = processor.entity_graph

        # constants
        num_orig_vertices = entity_graph.num_vertices()
        num_orig_edges = entity_graph.num_edges()

        host_v = self._get_entity_from_graph(NOVA_HOST_DATASOURCE,
                                             _TARGET_HOST,
                                             _TARGET_HOST,
                                             entity_graph)
        self.assertEqual('AVAILABLE', host_v[VProps.VITRAGE_AGGREGATED_STATE],
                         'host should be AVAILABLE when starting')

        # generate nagios alarm_a to trigger
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                     NagiosProperties.SERVICE: 'alarm_a'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        alarm_a_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, alarm_a_test,
                                           processor, _TARGET_HOST)
        alarms = self._get_alarms_on_host(host_v, entity_graph)
        self.assertThat(alarms, matchers.HasLength(1))
        self.assertEqual(num_orig_vertices + 1, entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + 1, entity_graph.num_edges())

        # generate nagios alarm_b to trigger
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                     NagiosProperties.SERVICE: 'alarm_b'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        alarm_b_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, alarm_b_test,
                                           processor, _TARGET_HOST)
        alarms = self._get_alarms_on_host(host_v, entity_graph)
        self.assertThat(alarms, matchers.HasLength(2))
        self.assertEqual(num_orig_vertices + 2, entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + 2, entity_graph.num_edges())

        # generate nagios alarm_c to trigger, alarm_d is raised
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.WARNING,
                     NagiosProperties.SERVICE: 'alarm_c'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        alarm_c_test = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, alarm_c_test,
                                           processor, _TARGET_HOST)
        alarms = self._get_alarms_on_host(host_v, entity_graph)
        self.assertThat(alarms, matchers.HasLength(4))
        self.assertEqual(num_orig_vertices + 4, entity_graph.num_vertices())
        self.assertEqual(num_orig_edges + 4, entity_graph.num_edges())

        # remove nagios alarm_b, alarm_d should not be removed
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.OK,
                     NagiosProperties.SERVICE: 'alarm_b'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        alarm_b_ok = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, alarm_b_ok,
                                           processor, _TARGET_HOST)
        alarms = self._get_alarms_on_host(host_v, entity_graph)
        self.assertThat(alarms, matchers.HasLength(3))

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_IS_DELETED: True}
        deleted_alarms = entity_graph.neighbors(host_v.vertex_id,
                                                vertex_attr_filter=query)
        self.assertEqual(num_orig_vertices + len(deleted_alarms) + 3,
                         entity_graph.num_vertices())

        query = {VProps.VITRAGE_IS_DELETED: True}
        deleted_edges = entity_graph.neighbors(host_v.vertex_id,
                                               edge_attr_filter=query)
        self.assertEqual(num_orig_edges + len(deleted_edges) + 3,
                         entity_graph.num_edges())

        # remove nagios alarm_a, alarm_d should be removed
        test_vals = {NagiosProperties.STATUS: NagiosTestStatus.OK,
                     NagiosProperties.SERVICE: 'alarm_a'}
        test_vals.update(_NAGIOS_TEST_INFO)
        generator = mock_driver.simple_nagios_alarm_generators(1, 1, test_vals)
        alarm_a_ok = mock_driver.generate_random_events_list(generator)[0]

        host_v = self.get_host_after_event(event_queue, alarm_a_ok,
                                           processor, _TARGET_HOST)
        alarms = self._get_alarms_on_host(host_v, entity_graph)
        self.assertThat(alarms, matchers.HasLength(1))

        query = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                 VProps.VITRAGE_IS_DELETED: True}
        deleted_alarms = entity_graph.neighbors(host_v.vertex_id,
                                                vertex_attr_filter=query)
        self.assertEqual(num_orig_vertices + len(deleted_alarms) + 1,
                         entity_graph.num_vertices())

        query = {VProps.VITRAGE_IS_DELETED: True}
        deleted_edges = entity_graph.neighbors(host_v.vertex_id,
                                               edge_attr_filter=query)
        self.assertEqual(num_orig_edges + len(deleted_edges) + 1,
                         entity_graph.num_edges())

    def get_host_after_event(self, event_queue, nagios_event,
                             processor, target_host):
        processor.process_event(nagios_event)
        self._consume_queue(event_queue, processor)
        host_v = self._get_entity_from_graph(NOVA_HOST_DATASOURCE,
                                             target_host,
                                             target_host,
                                             processor.entity_graph)
        return host_v

    def _init_system(self):
        processor = self._create_processor_with_graph()
        event_queue = queue.Queue()

        def actions_callback(event_type, data):
            """Mock notify method

            Mocks vitrage.messaging.VitrageNotifier.notify(event_type, data)

            :param event_type: is currently always the same and is ignored
            :param data:
            """
            event_queue.put(data)

        evaluator = ScenarioEvaluator(processor.entity_graph,
                                      self.scenario_repository,
                                      actions_callback,
                                      enabled=True)
        return event_queue, processor, evaluator

    @staticmethod
    def _get_entity_from_graph(entity_type, entity_name,
                               entity_id,
                               entity_graph):
        vertex_attrs = {VProps.VITRAGE_TYPE: entity_type,
                        VProps.ID: entity_id,
                        VProps.NAME: entity_name}
        vertices = entity_graph.get_vertices(vertex_attr_filter=vertex_attrs)
        return vertices[0]

    @staticmethod
    def _get_deduced_alarms_on_host(host_v, entity_graph):
        v_id = host_v.vertex_id
        vertex_attrs = {VProps.NAME: 'deduced_alarm',
                        VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE,
                        VProps.VITRAGE_IS_DELETED: False, }
        return entity_graph.neighbors(v_id=v_id,
                                      vertex_attr_filter=vertex_attrs)

    @staticmethod
    def _get_alarms_on_host(host_v, entity_graph):
        v_id = host_v.vertex_id
        vertex_attrs = {VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                        VProps.VITRAGE_IS_DELETED: False, }
        return entity_graph.neighbors(v_id=v_id,
                                      vertex_attr_filter=vertex_attrs)

    @staticmethod
    def _get_alarm_causes(alarm_v, entity_graph):
        v_id = alarm_v.vertex_id
        edge_attrs = {EProps.RELATIONSHIP_TYPE: EdgeLabel.CAUSES,
                      EProps.VITRAGE_IS_DELETED: False, }
        return entity_graph.neighbors(v_id=v_id, edge_attr_filter=edge_attrs)
