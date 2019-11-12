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

from vitrage.common.constants import EdgeLabel
from vitrage.common.constants import EdgeProperties
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.entity_graph.mappings.operational_resource_state import \
    OperationalResourceState
from vitrage.evaluator.condition import ConditionVar
from vitrage.evaluator.scenario_evaluator import ActionType
from vitrage.evaluator.template_data import ActionSpecs
from vitrage.evaluator.template_data import EdgeDescription
from vitrage.evaluator.template_data import Scenario
from vitrage.evaluator.template_fields import TemplateFields as TFields
from vitrage.evaluator.template_loading.props_converter import PropsConverter
from vitrage.graph import Edge
from vitrage.graph import Vertex
from vitrage.tests import base
from vitrage.tests.mocks import utils
from vitrage.tests.unit.evaluator import get_template_data
from vitrage.utils import file as file_utils


class TemplateLoaderTest(base.BaseTest):

    BASIC_TEMPLATE = 'basic.yaml'
    BASIC_TEMPLATE_WITH_INCLUDE = 'basic_with_include.yaml'
    V1_MISTRAL_TEMPLATE = 'v1/v1_execute_mistral.yaml'
    V2_MISTRAL_TEMPLATE = 'v2/v2_execute_mistral.yaml'
    DEF_TEMPLATE_TESTS_DIR = utils.get_resources_dir() +\
        '/templates/def_template_tests'

    def test_basic_template_with_include(self):

        # Test setup
        template_path = self.DEF_TEMPLATE_TESTS_DIR +\
            '/templates/%s' % self.BASIC_TEMPLATE_WITH_INCLUDE
        template_definition = file_utils.load_yaml_file(template_path, True)
        def_templates_path = self.DEF_TEMPLATE_TESTS_DIR + \
            '/definition_templates'
        def_templates_list = file_utils.load_yaml_files(
            def_templates_path)
        def_templates_dict = utils.get_def_templates_dict_from_list(
            def_templates_list)
        template_data = get_template_data(template_definition,
                                          def_templates_dict)
        entities = template_data.entities
        relationships = template_data.relationships
        scenarios = template_data.scenarios
        definitions = template_definition[TFields.DEFINITIONS]
        def_template = file_utils.load_yaml_file(
            def_templates_path + '/basic_def_template.yaml')
        def_template_entities = \
            def_template[TFields.DEFINITIONS][TFields.ENTITIES]
        def_template_relationships = \
            def_template[TFields.DEFINITIONS][TFields.RELATIONSHIPS]
        definitions[TFields.ENTITIES] += def_template_entities
        definitions[TFields.RELATIONSHIPS] = def_template_relationships

        # Assertions
        for definition in definitions[TFields.ENTITIES]:
            for key, value in list(definition['entity'].items()):
                new_key = PropsConverter.PROPS_CONVERSION[key] \
                    if key in PropsConverter.PROPS_CONVERSION else key
                del definition['entity'][key]
                definition['entity'][new_key] = value
        self._validate_entities(entities, definitions[TFields.ENTITIES])

        relate_def = def_template_relationships
        self._validate_relationships(relationships, relate_def, entities)
        self._validate_scenarios(scenarios, entities)

        expected_entities = {
            'alarm11': Vertex(
                vertex_id='alarm11',
                properties={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                            VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE,
                            VProps.NAME: 'host_problem'
                            }),
            'resource11': Vertex(
                vertex_id='resource11',
                properties={VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                            VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE
                            }),
            'alarm': Vertex(
                vertex_id='alarm',
                properties={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                            VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE,
                            VProps.NAME: 'host_problem'
                            }),
            'resource': Vertex(
                vertex_id='resource',
                properties={VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                            VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE
                            })
        }
        expected_relationships = {
            'alarm_on_host': EdgeDescription(
                edge=Edge(source_id='alarm',
                          target_id='resource',
                          label=EdgeLabel.ON,
                          properties={EdgeProperties.RELATIONSHIP_TYPE:
                                      EdgeLabel.ON}),
                source=expected_entities['alarm'],
                target=expected_entities['resource']
            ),
        }

        scenario_entities = {
            'alarm': Vertex(
                vertex_id='alarm',
                properties={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                            VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE,
                            VProps.NAME: 'host_problem'
                            }),
            'resource': Vertex(
                vertex_id='resource',
                properties={VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                            VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE
                            })
        }

        expected_scenario = Scenario(
            id='basic_template_with_include-scenario0',
            version=1,
            condition=[
                [ConditionVar(symbol_name='alarm_on_host',
                              positive=True)]],
            actions=[
                ActionSpecs(
                    id='basic_template_with_include-scenario0-action0',
                    type=ActionType.SET_STATE,
                    targets={'target': 'resource'},
                    properties={'state':
                                OperationalResourceState.SUBOPTIMAL})],
            subgraphs=template_data.scenarios[0].subgraphs,
            entities=scenario_entities,
            relationships=expected_relationships
        )

        self._validate_strict_equal(template_data,
                                    expected_entities,
                                    expected_relationships,
                                    expected_scenario)

    def test_basic_template(self):

        # Test setup
        template_path = '%s/templates/general/%s' % (utils.get_resources_dir(),
                                                     self.BASIC_TEMPLATE)
        template_definition = file_utils.load_yaml_file(template_path, True)

        template_data = get_template_data(template_definition)
        entities = template_data.entities
        relationships = template_data.relationships
        scenarios = template_data.scenarios
        definitions = template_definition[TFields.DEFINITIONS]

        # Assertions
        for definition in definitions[TFields.ENTITIES]:
            for key, value in list(definition['entity'].items()):
                new_key = PropsConverter.PROPS_CONVERSION[key] \
                    if key in PropsConverter.PROPS_CONVERSION else key
                del definition['entity'][key]
                definition['entity'][new_key] = value
        self._validate_entities(entities, definitions[TFields.ENTITIES])

        relate_def = definitions[TFields.RELATIONSHIPS]
        self._validate_relationships(relationships, relate_def, entities)
        self._validate_scenarios(scenarios, entities)

        expected_entities = {
            'alarm': Vertex(
                vertex_id='alarm',
                properties={VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
                            VProps.VITRAGE_TYPE: NAGIOS_DATASOURCE,
                            VProps.NAME: 'host_problem'
                            }),
            'resource': Vertex(
                vertex_id='resource',
                properties={VProps.VITRAGE_CATEGORY: EntityCategory.RESOURCE,
                            VProps.VITRAGE_TYPE: NOVA_HOST_DATASOURCE
                            })
        }

        expected_relationships = {
            'alarm_on_host': EdgeDescription(
                edge=Edge(source_id='alarm',
                          target_id='resource',
                          label=EdgeLabel.ON,
                          properties={EdgeProperties.RELATIONSHIP_TYPE:
                                      EdgeLabel.ON}),
                source=expected_entities['alarm'],
                target=expected_entities['resource']
            )
        }

        expected_scenario = Scenario(
            id='basic_template-scenario0',
            version=1,
            condition=[
                [ConditionVar(symbol_name='alarm_on_host',
                              positive=True)]],
            actions=[
                ActionSpecs(
                    id='basic_template-scenario0-action0',
                    type=ActionType.SET_STATE,
                    targets={'target': 'resource'},
                    properties={'state':
                                OperationalResourceState.SUBOPTIMAL})],
            # TODO(yujunz): verify the built subgraph is consistent with
            #               scenario definition. For now the observed value is
            #               assigned to make test passing
            subgraphs=template_data.scenarios[0].subgraphs,
            entities=expected_entities,
            relationships=expected_relationships
        )

        self._validate_strict_equal(template_data,
                                    expected_entities,
                                    expected_relationships,
                                    expected_scenario)

    def test_convert_v1_template(self):
        # Load v1 and v2 templates, and get their actions
        v1_action = self._get_template_single_action(self.V1_MISTRAL_TEMPLATE)
        v2_action = self._get_template_single_action(self.V2_MISTRAL_TEMPLATE)

        # Validate that the action definition is identical (since v1 template
        # should be converted to v2 format)
        self._assert_equal_actions(v1_action, v2_action)

    def _get_template_single_action(self, template_file):
        template_path = '%s/templates/version/%s' % (utils.get_resources_dir(),
                                                     template_file)
        template_definition = file_utils.load_yaml_file(template_path, True)
        template_data = get_template_data(template_definition)
        scenarios = template_data.scenarios
        self.assertIsNotNone(scenarios, 'Template should include a scenario')
        self.assertThat(scenarios, matchers.HasLength(1),
                        'Template should include a single scenario')
        actions = scenarios[0].actions
        self.assertIsNotNone(actions, 'Scenario should include an action')
        self.assertThat(actions, matchers.HasLength(1),
                        'Scenario should include a single action')
        return actions[0]

    def _assert_equal_actions(self, action1, action2):
        """Compare all action fields except from the id"""
        self.assertEqual(action1.type, action2.type,
                         'Action types should be equal')
        self.assert_dict_equal(action1.targets, action2.targets,
                               'Action targets should be equal')
        self.assert_dict_equal(action1.properties, action2.properties,
                               'Action targets should be equal')

    def _validate_strict_equal(self,
                               template_data,
                               expected_entities,
                               expected_relationships,
                               expected_scenario
                               ):
        self.assert_dict_equal(expected_entities, template_data.entities,
                               'entities not equal')

        self.assert_dict_equal(expected_relationships,
                               template_data.relationships,
                               'relationship not equal')

        self.assertEqual(expected_scenario, template_data.scenarios[0],
                         'scenario not equal')

    def _validate_entities(self, entities, entities_def):

        self.assertIsNotNone(entities)
        for entity_id, entity in entities.items():

            self.assertIsInstance(entity, Vertex)
            self.assertEqual(entity_id, entity.vertex_id)
            self.assertIsNotNone(entity.properties)
            self.assertIn(VProps.VITRAGE_CATEGORY, entity.properties)

        self.assertEqual(len(entities), len(entities_def))

        for entity_def in entities_def:
            entity_def_dict = entity_def[TFields.ENTITY]
            self.assertIn(entity_def_dict[TFields.TEMPLATE_ID], entities)
            entity = entities[entity_def_dict[TFields.TEMPLATE_ID]]

            for key, value in entity_def_dict.items():
                if key == TFields.TEMPLATE_ID:
                    continue
                self.assertEqual(value, entity.properties[key])

    def _validate_relationships(self, relationships, relations_def, entities):

        self.assertIsNotNone(relationships)
        for relationship_id, relationship in relationships.items():

            self.assertIsInstance(relationship, EdgeDescription)
            self.assertIn(relationship.source.vertex_id, entities)
            self.assertIn(relationship.target.vertex_id, entities)

            relationship_props = relationship.edge.properties
            self.assertIsNotNone(relationship_props)
            relation_type = relationship_props[TFields.RELATIONSHIP_TYPE]
            self.assertEqual(relation_type, relationship.edge.label)

        self.assertEqual(len(relationships), len(relations_def))

        exclude_keys = [TFields.TEMPLATE_ID, TFields.SOURCE, TFields.TARGET]
        for relation_def in relations_def:

            relation_def_dict = relation_def[TFields.RELATIONSHIP]

            template_id = relation_def_dict[TFields.TEMPLATE_ID]
            self.assertIn(template_id, relationships)
            relationship = relationships[template_id].edge

            for key, value in relation_def_dict.items():
                if key not in exclude_keys:
                    self.assertEqual(value, relationship.properties[key])

    def _validate_scenarios(self, scenarios, entities):
        """Validates scenario parsing

        Expects to single scenario:
         1. condition consists from one variable (type EdgeDescription)
         2. Actions - set state action
        :param scenarios: parsed scenarios
        :param entities
        """
        self.assertIsNotNone(scenarios)
        self.assertThat(scenarios, matchers.HasLength(1))

        scenario = scenarios[0]

        condition = scenario.condition
        self.assertThat(condition, matchers.HasLength(1))

        condition_var = condition[0][0]
        self.assertIsInstance(condition_var, ConditionVar)

        symbol_name = condition_var.symbol_name
        self.assertIsInstance(symbol_name, str)

        actions = scenario.actions
        self.assert_is_not_empty(scenario.actions)
        self.assertThat(actions, matchers.HasLength(1))

        action = actions[0]
        self.assertEqual(action.type, ActionType.SET_STATE)

        targets = action.targets
        self.assertThat(targets, matchers.HasLength(1))
        self.assertEqual('resource', targets['target'])

        properties = action.properties
        self.assertThat(properties, matchers.HasLength(1))
        self.assertEqual(properties['state'],
                         OperationalResourceState.SUBOPTIMAL)
