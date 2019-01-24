# Copyright 2017 - Nokia
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

from vitrage.evaluator.condition import SymbolResolver
from vitrage.evaluator.template_data import EdgeDescription
from vitrage.evaluator.template_validation.content.v1.scenario_validator \
    import get_condition_common_targets
from vitrage.tests import base
from vitrage.tests.mocks import utils
from vitrage.tests.unit.evaluator import get_template_data
from vitrage.utils import file as file_utils


CONDITION_TEMPLATES_DIR = '%s/templates/evaluator/conditions/%s'


class ConditionTest(base.BaseTest):

    def test_validate_scenario_target_one_edge_condition(self):
        self._check_get_condition_common_targets('one_edge.yaml',
                                                 ['alarm1', 'instance'])

    def test_validate_scenario_target_one_vertex_condition(self):
        self._check_get_condition_common_targets('one_vertex.yaml',
                                                 ['instance2'])

    def test_validate_scenario_target_simple_or_condition(self):
        self._check_get_condition_common_targets('simple_or.yaml',
                                                 ['instance3'])

    def test_validate_scenario_target_simple_or2_condition(self):
        self._check_get_condition_common_targets('simple_or2.yaml',
                                                 ['instance'])

    def test_validate_scenario_target_simple_or3_condition(self):
        self._check_get_condition_common_targets('simple_or3.yaml',
                                                 ['instance4'])

    def test_validate_scenario_target_simple_or_unsupported_condition(self):
        self._check_get_condition_common_targets('simple_or_unsupported.yaml',
                                                 [])

    def test_validate_scenario_target_simple_and_condition(self):
        self._check_get_condition_common_targets(
            'simple_and.yaml', ['alarm2', 'alarm3', 'instance'])

    def test_validate_scenario_target_simple_and2_condition(self):
        self._check_get_condition_common_targets(
            'simple_and2.yaml', ['alarm2', 'alarm3', 'instance', 'host'])

    def test_validate_scenario_target_complex1_condition(self):
        self._check_get_condition_common_targets('complex1.yaml', ['instance'])

    def test_validate_scenario_target_complex2_condition(self):
        self._check_get_condition_common_targets('complex2.yaml',
                                                 ['alarm4', 'host'])

    def test_validate_scenario_target_not_edge_unsupported_condition(self):
        self._check_get_condition_common_targets('not_edge_unsupported.yaml',
                                                 [])

    def test_validate_scenario_target_not_or_unsupported__condition(self):
        self._check_get_condition_common_targets('not_or_unsupported.yaml',
                                                 [])

    def test_validate_scenario_target_not_or_unsupported2_condition(self):
        self._check_get_condition_common_targets('not_or_unsupported2.yaml',
                                                 [])

    def test_validate_scenario_target_complex_not_condition(self):
        self._check_get_condition_common_targets('complex_not.yaml',
                                                 ['instance'])

    def test_validate_scenario_target_complex_not_unsupported_condition(self):
        self._check_get_condition_common_targets(
            'complex_not_unsupported.yaml', [])

    def _check_get_condition_common_targets(self,
                                            template_name,
                                            valid_targets):
        template_path = CONDITION_TEMPLATES_DIR % (utils.get_resources_dir(),
                                                   template_name)
        template_definition = file_utils.load_yaml_file(template_path, True)

        template_data = get_template_data(template_definition)
        definitions_index = template_data.entities.copy()
        definitions_index.update(template_data.relationships)

        common_targets = get_condition_common_targets(
            template_data.scenarios[0].condition,
            definitions_index,
            self.ConditionSymbolResolver())

        self.assertIsNotNone(common_targets)
        self.assertTrue(common_targets == set(valid_targets))

    class ConditionSymbolResolver(SymbolResolver):
        def is_relationship(self, symbol):
            return isinstance(symbol, EdgeDescription)

        def get_relationship_source_id(self, relationship):
            return relationship.source.vertex_id

        def get_relationship_target_id(self, relationship):
            return relationship.target.vertex_id

        def get_entity_id(self, entity):
            return entity.vertex_id
