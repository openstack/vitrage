# Copyright 2019 - Nokia
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

from vitrage.evaluator.template_data import ActionSpecs
from vitrage.evaluator.template_data import EdgeDescription
from vitrage.evaluator.template_data import Scenario
from vitrage.graph.driver.networkx_graph import NXGraph
from vitrage.graph import Edge
from vitrage.graph import Vertex
from vitrage.tests.base import BaseTest
from vitrage.tests.functional.test_configuration import TestConfiguration
from vitrage.tests.mocks.utils import get_resources_dir
from vitrage.tests.unit.evaluator import get_template_data
from vitrage.utils import file as file_utils


class TemplateLoaderV3Test(BaseTest, TestConfiguration):

    expected_entities = {
        'host_ssh_alarm': Vertex('host_ssh_alarm', {
            'rawtext': 'host ssh is down', 'vitrage_type': 'zabbix'}),
        'host': Vertex('host', {'vitrage_type': 'nova.host'}),
        'foo': Vertex('foo', {'name.regex': 'kuku'}),
        'host_network_alarm': Vertex('host_network_alarm', {
            'rawtext': 'host network interface is down',
            'vitrage_type': 'zabbix',
        }),
        'instance': Vertex('instance', {'vitrage_type': 'nova.instance'}),
    }
    expected_relationships = {
        'host_ssh_alarm__on__host': EdgeDescription(
            Edge('host_ssh_alarm', 'host', 'on', {}),
            Vertex('host_ssh_alarm', {
                'rawtext': 'host ssh is down', 'vitrage_type': 'zabbix'
            }),
            Vertex('host', {'vitrage_type': 'nova.host'})),
        'host__contains__instance': EdgeDescription(
            Edge('host', 'instance', 'contains', {}),
            Vertex('host', {'vitrage_type': 'nova.host'}),
            Vertex('instance', {'vitrage_type': 'nova.instance'})),
        'host_network_alarm__on__host': EdgeDescription(
            Edge('host_network_alarm', 'host', 'on', {}),
            Vertex('host_network_alarm', {
                'rawtext': 'host network interface is down',
                'vitrage_type': 'zabbix'
            }),
            Vertex('host', {'vitrage_type': 'nova.host'})),
    }

    def setUp(self):
        super(TemplateLoaderV3Test, self).setUp()
        self.add_db()

    def _load_scenarios(self, file=None, content=None):
        if file and not content:
            content = self._get_yaml(file)
        return get_template_data(content).scenarios

    def _assert_scenario_equal(self, expected, observed):

        # Basic
        self.assertEqual(expected.id, observed.id)
        self.assertEqual(expected.version, observed.version)
        self.assertEqual(expected.condition, observed.condition)  # is None

        # Actions
        self.assertEqual(len(expected.actions), len(observed.actions),
                         'actions count')
        for j in range(len(expected.actions)):
            expected_action = expected.actions[j]
            observed_action = observed.actions[j]
            self.assertEqual(expected_action.id, observed_action.id)
            self.assertEqual(expected_action.type, observed_action.type)
            self.assertEqual(expected_action.properties,
                             observed_action.properties)
            if expected_action.type == 'execute_mistral':
                continue
            self.assertEqual(expected_action.targets, observed_action.targets)

        # Subgraphs
        self.assertEqual(len(expected.subgraphs), len(observed.subgraphs),
                         'subgraphs count')
        for j in range(len(expected.subgraphs)):
            expected_subgraph = expected.subgraphs[j]
            observed_subgraph = observed.subgraphs[j]
            self.assert_graph_equal(expected_subgraph, observed_subgraph)

        # Entities
        self.assert_dict_equal(expected.entities, observed.entities,
                               'entities comparison')
        self.assert_dict_equal(expected.relationships, observed.relationships,
                               'relationships comparison')

    @staticmethod
    def _get_yaml(filename):
        path = '%s/templates/v3_templates/%s' % (get_resources_dir(), filename)
        return file_utils.load_yaml_file(path)

    def test_scenarios(self):
        observed_scenarios = self._load_scenarios('valid_actions.yaml')
        self.assertEqual(6, len(observed_scenarios), 'scenarios count')

    def test_scenario_0(self):
        observed_scenarios = self._load_scenarios('valid_actions.yaml')
        expected_scenario = Scenario(
            'valid actions-scenario0',
            '3',
            None,
            [
                ActionSpecs(
                    'valid actions-scenario0-action0',
                    'set_state',
                    {'target': 'host'},
                    {'state': 'ERROR'}),
                ActionSpecs(
                    'valid actions-scenario0-action1',
                    'raise_alarm',
                    {'target': 'host'},
                    {'severity': 'WARNING', 'alarm_name': 'ddd'}),
                ActionSpecs(
                    'valid actions-scenario0-action2',
                    'mark_down',
                    {'target': 'host'},
                    {}),
                ActionSpecs(
                    'valid actions-scenario0-action3',
                    'execute_mistral',
                    {'target': 'host'},
                    {'input': {'farewell': 'get_attr(host, name) bla bla'},
                     'workflow': 'wf_1234'}),
            ],
            [
                NXGraph(
                    vertices=[
                        Vertex('host_ssh_alarm',
                               {
                                   'rawtext': 'host ssh is down',
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'zabbix',
                                   'vitrage_is_deleted': False,
                               }),
                        Vertex('host',
                               {
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'nova.host',
                                   'vitrage_is_deleted': False,
                               })
                    ],
                    edges=[
                        Edge('host_ssh_alarm', 'host', 'on',
                             {
                                 'vitrage_is_deleted': False,
                                 'negative_condition': False
                             })
                    ])
            ],
            TemplateLoaderV3Test.expected_entities,
            TemplateLoaderV3Test.expected_relationships)
        self._assert_scenario_equal(
            expected_scenario,
            observed_scenarios[0])

    def test_scenario_1(self):
        observed_scenarios = self._load_scenarios('valid_actions.yaml')
        expected_scenario = Scenario(
            'valid actions-scenario1',
            '3',
            None,
            [
                ActionSpecs(
                    'valid actions-scenario1-action0',
                    'add_causal_relationship',
                    {
                        'target': 'host_ssh_alarm',
                        'source': 'host_network_alarm',
                    },
                    {}),
            ],
            [
                NXGraph(
                    vertices=[
                        Vertex('host_ssh_alarm',
                               {
                                   'rawtext': 'host ssh is down',
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'zabbix',
                                   'vitrage_is_deleted': False,
                               }),
                        Vertex('host_network_alarm',
                               {
                                   'rawtext': 'host network interface is down',
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'zabbix',
                                   'vitrage_is_deleted': False,
                               }),
                        Vertex('host',
                               {
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'nova.host',
                                   'vitrage_is_deleted': False,
                               })
                    ],
                    edges=[
                        Edge('host_ssh_alarm', 'host', 'on',
                             {
                                 'vitrage_is_deleted': False,
                                 'negative_condition': False
                             }),
                        Edge('host_network_alarm', 'host', 'on',
                             {
                                 'vitrage_is_deleted': False,
                                 'negative_condition': False
                             })
                    ])
            ],
            TemplateLoaderV3Test.expected_entities,
            TemplateLoaderV3Test.expected_relationships)
        self._assert_scenario_equal(
            expected_scenario,
            observed_scenarios[1])

    def test_scenario_2(self):
        observed_scenarios = self._load_scenarios('valid_actions.yaml')
        expected_scenario = Scenario(
            'valid actions-scenario2',
            '3',
            None,
            [
                ActionSpecs(
                    'valid actions-scenario2-action0',
                    'raise_alarm',
                    {'target': 'instance'},
                    {
                        'severity': 'WARNING',
                        'alarm_name': 'instance is down',
                        'causing_alarm':
                            'get_attr(host_ssh_alarm, vitrage_id)',
                    }),
                ActionSpecs(
                    'valid actions-scenario2-action1',
                    'set_state',
                    {'target': 'instance'},
                    {'state': 'SUBOPTIMAL'}),
            ],
            [
                NXGraph(
                    vertices=[
                        Vertex('host_ssh_alarm',
                               {
                                   'rawtext': 'host ssh is down',
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'zabbix',
                                   'vitrage_is_deleted': False,
                               }),
                        Vertex('instance',
                               {
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'nova.instance',
                                   'vitrage_is_deleted': False,
                               }),
                        Vertex('host',
                               {
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'nova.host',
                                   'vitrage_is_deleted': False,
                               }),
                    ],
                    edges=[
                        Edge('host_ssh_alarm', 'host', 'on',
                             {
                                 'vitrage_is_deleted': False,
                                 'negative_condition': False
                             }),
                        Edge('host', 'instance', 'contains',
                             {
                                 'vitrage_is_deleted': False,
                                 'negative_condition': False
                             })
                    ])
            ],
            TemplateLoaderV3Test.expected_entities,
            TemplateLoaderV3Test.expected_relationships)
        self._assert_scenario_equal(
            expected_scenario,
            observed_scenarios[2])

    def test_scenario_3(self):
        observed_scenarios = self._load_scenarios('valid_actions.yaml')
        expected_scenario = Scenario(
            'valid actions-scenario3',
            '3',
            None,
            [
                ActionSpecs(
                    'valid actions-scenario3-action0',
                    'mark_down',
                    {'target': 'host'},
                    {}),
            ],
            [
                NXGraph(
                    vertices=[
                        Vertex('instance',
                               {
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'nova.instance',
                                   'vitrage_is_deleted': False,
                               }),
                        Vertex('host',
                               {
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'nova.host',
                                   'vitrage_is_deleted': False,
                               }),
                    ],
                    edges=[
                        Edge('host', 'instance', 'contains',
                             {
                                 'vitrage_is_deleted': False,
                                 'negative_condition': False
                             })
                    ]),
                NXGraph(
                    vertices=[
                        Vertex('host_ssh_alarm',
                               {
                                   'rawtext': 'host ssh is down',
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'zabbix',
                                   'vitrage_is_deleted': False,
                               }),
                        Vertex('host',
                               {
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'nova.host',
                                   'vitrage_is_deleted': False,
                               }),
                    ],
                    edges=[
                        Edge('host_ssh_alarm', 'host', 'on',
                             {
                                 'vitrage_is_deleted': True,
                                 'negative_condition': True,
                             }),
                    ]),
            ],
            TemplateLoaderV3Test.expected_entities,
            TemplateLoaderV3Test.expected_relationships)
        self._assert_scenario_equal(
            expected_scenario,
            observed_scenarios[3])

    def test_scenario_4(self):
        observed_scenarios = self._load_scenarios('valid_actions.yaml')
        expected_scenario = Scenario(
            'valid actions-scenario4',
            '3',
            None,
            [
                ActionSpecs(
                    'valid actions-scenario4-action0',
                    'mark_down',
                    {'target': 'host'},
                    {}),
            ],
            [
                NXGraph(
                    vertices=[
                        Vertex('host',
                               {
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'nova.host',
                                   'vitrage_is_deleted': False,
                               }),
                    ]),
            ],
            TemplateLoaderV3Test.expected_entities,
            TemplateLoaderV3Test.expected_relationships)
        self._assert_scenario_equal(
            expected_scenario,
            observed_scenarios[4])

    def test_scenario_5(self):
        observed_scenarios = self._load_scenarios('valid_actions.yaml')
        expected_scenario = Scenario(
            'valid actions-scenario5',
            '3',
            None,
            [
                ActionSpecs(
                    'valid actions-scenario5-action0',
                    'mark_down',
                    {'target': 'host'},
                    {}),
            ],
            [
                NXGraph(
                    vertices=[
                        Vertex('host_ssh_alarm',
                               {
                                   'rawtext': 'host ssh is down',
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'zabbix',
                                   'vitrage_is_deleted': False,
                               }),
                        Vertex('instance',
                               {
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'nova.instance',
                                   'vitrage_is_deleted': False,
                               }),
                        Vertex('host',
                               {
                                   'vitrage_is_placeholder': False,
                                   'vitrage_type': 'nova.host',
                                   'vitrage_is_deleted': False,
                               }),
                    ],
                    edges=[
                        Edge('host_ssh_alarm', 'host', 'on',
                             {
                                 'vitrage_is_deleted': True,
                                 'negative_condition': True
                             }),
                        Edge('host', 'instance', 'contains',
                             {
                                 'vitrage_is_deleted': True,
                                 'negative_condition': True
                             })
                    ]
                ),
            ],
            TemplateLoaderV3Test.expected_entities,
            TemplateLoaderV3Test.expected_relationships)
        self._assert_scenario_equal(
            expected_scenario,
            observed_scenarios[5])
