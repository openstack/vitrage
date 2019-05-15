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

from testtools import matchers

from vitrage.common.constants import EntityCategory
from vitrage.common.constants import TemplateTypes as TType
from vitrage.common.constants import VertexProperties as VProps
from vitrage.evaluator.scenario_repository import ScenarioRepository
from vitrage.evaluator.template_validation.template_syntax_validator import \
    syntax_validation
from vitrage.graph import Vertex
from vitrage.tests import base
from vitrage.tests.base import IsEmpty
from vitrage.tests.functional.test_configuration import TestConfiguration
from vitrage.tests.mocks import utils
from vitrage.utils import file as file_utils


class ScenarioRepositoryTest(base.BaseTest, TestConfiguration):
    def setUp(self):
        super(ScenarioRepositoryTest, self).setUp()
        self.add_db()
        templates_dir = utils.get_resources_dir() + '/templates/general'
        self.add_templates(templates_dir)
        templates_dir_path = templates_dir
        self.template_defs = file_utils.load_yaml_files(templates_dir_path)
        self.scenario_repository = ScenarioRepository()

    def test_template_loader(self):

        # Test Action
        scenario_repository = ScenarioRepository()

        # Test assertions
        self.assertIsNotNone(scenario_repository)
        self.assertThat(scenario_repository.templates,
                        matchers.HasLength(2),
                        'scenario_repository.templates '
                        'should contain all valid templates')

    def test_init_scenario_repository(self):

        # Test Setup
        valid_template_counter = 0
        for template_definition in self.template_defs:
            syntax_validation_result = syntax_validation(template_definition)
            if syntax_validation_result.is_valid_config:
                valid_template_counter += 1

        # Test assertions
        self.assertIsNotNone(self.scenario_repository)

        scenario_templates = self.scenario_repository.templates
        # there is one bad template
        self.assertThat(scenario_templates,
                        matchers.HasLength(valid_template_counter),
                        'scenario_repository.templates '
                        'should contain all valid templates')

        entity_equivalences = self.scenario_repository.entity_equivalences
        for entity_props, equivalence in entity_equivalences.items():
            # Example structure of entity_equivalences
            #   { A: (A, B, C),
            #     B: (A, B, C),
            #     C: (A, B, C)}
            # Verify entity itself is also included. It is not required, but
            # worth noting when handling equivalence
            self.assertTrue(entity_props in equivalence)
            for equivalent_props in equivalence:
                # Verify equivalent scenarios are present in repository
                self.assertTrue(equivalent_props in
                                self.scenario_repository.entity_scenarios)

    def test_get_scenario_by_edge(self):
        pass

    def test_get_scenario_by_entity(self):
        pass

    def test_add_template(self):
        pass


class RegExTemplateTest(base.BaseTest, TestConfiguration):

    def setUp(self):
        super(RegExTemplateTest, self).setUp()
        templates_dir = utils.get_resources_dir() + '/templates/regex'
        self.add_db()
        self.add_templates(templates_dir)
        self.scenario_repository = ScenarioRepository()

    def test_basic_regex(self):

        event_properties = {
            "time": 121354,
            "vitrage_type": "zabbix",
            "vitrage_category": "ALARM",
            "rawtext": "Interface virtual-0 down on {HOST.NAME}",
            "host": "some_host_kukoo"
        }
        event_vertex = Vertex(vertex_id="test_vertex",
                              properties=event_properties)
        relevant_scenarios = \
            self.scenario_repository.get_scenarios_by_vertex(
                event_vertex)
        self.assertThat(relevant_scenarios, matchers.HasLength(1))
        relevant_scenario = relevant_scenarios[0]
        self.assertEqual("zabbix_alarm_pass", relevant_scenario[0].vertex_id)

    def test_regex_with_exact_match(self):

        event_properties = {
            "time": 121354,
            "vitrage_type": "zabbix",
            "vitrage_category": "ALARM",
            "rawtext": "Public interface host43 down",
            "host": "some_host_kukoo"
        }
        event_vertex = Vertex(vertex_id="test_vertex",
                              properties=event_properties)
        relevant_scenarios = \
            self.scenario_repository.get_scenarios_by_vertex(
                event_vertex)
        self.assertThat(relevant_scenarios, matchers.HasLength(1))
        relevant_scenario = relevant_scenarios[0]
        self.assertEqual("exact_match", relevant_scenario[0].vertex_id)

    def test_basic_regex_with_no_match(self):

        event_properties = {
            "time": 121354,
            "vitrage_type": "zabbix",
            "vitrage_category": "ALARM",
            "rawtext": "No Match",
            "host": "some_host_kukoo"
        }
        event_vertex = Vertex(vertex_id="test_vertex",
                              properties=event_properties)
        relevant_scenarios = \
            self.scenario_repository.get_scenarios_by_vertex(
                event_vertex)
        self.assertThat(relevant_scenarios, IsEmpty())


class EquivalentScenarioTest(base.BaseTest, TestConfiguration):
    def setUp(self):
        super(EquivalentScenarioTest, self).setUp()
        templates_dir = utils.get_resources_dir() + \
            '/templates/equivalent_scenarios/'
        equivalences_dir = templates_dir + '/equivalences'
        def_templates_dir = utils.get_resources_dir() + \
            '/templates/def_template_tests'
        self.add_db()
        self.add_templates(templates_dir)
        self.add_templates(equivalences_dir,
                           TType.EQUIVALENCE)
        self.add_templates(def_templates_dir,
                           TType.DEFINITION)
        self.scenario_repository = ScenarioRepository()

    def test_expansion(self):
        entity_scenarios = self.scenario_repository.entity_scenarios
        for key, scenarios in entity_scenarios.items():
            if (VProps.VITRAGE_CATEGORY, EntityCategory.ALARM) in key:
                # scenarios expanded on the other alarm
                self.assertThat(scenarios, matchers.HasLength(2))
            if (VProps.VITRAGE_CATEGORY, EntityCategory.RESOURCE) in key:
                # Scenarios expanded on the two alarms. Each alarm is expanded
                # to two equivalent alarms. Thus 2 x 2 = 4 in total
                self.assertThat(scenarios, matchers.HasLength(4))
        # each relationship is expand to two. Thus 2 x 2 = 4 in total
        relationships = self.scenario_repository.relationship_scenarios.keys()
        self.assertThat(relationships, matchers.HasLength(4))
