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

from vitrage.common.exception import VitrageError
from vitrage.evaluator.condition import get_condition_common_targets
from vitrage.evaluator.condition import parse_condition
from vitrage.evaluator.condition import SymbolResolver
from vitrage.evaluator.template_data import EdgeDescription
from vitrage.evaluator.template_data import ENTITY
from vitrage.evaluator.template_data import RELATIONSHIP
from vitrage.evaluator.template_data import Scenario
from vitrage.evaluator.template_fields import TemplateFields as TFields
from vitrage.evaluator.template_loading.subgraph_builder import \
    SubGraphBuilder
from vitrage.graph import Vertex

LOG = log.getLogger(__name__)


class ScenarioLoader(object):

    def __init__(self, template_schema, name, entities, relationships):
        self.name = name
        self._template_schema = template_schema
        self._template_entities = entities
        self._template_relationships = relationships

        self.entities = {}
        self.relationships = {}
        self.valid_target = None

    def build_scenarios(self, scenarios_defs):
        scenarios = []
        for counter, scenario_def in enumerate(scenarios_defs):
            scenario_id = "%s-scenario%s" % (self.name, counter)
            scenario_dict = scenario_def[TFields.SCENARIO]
            condition = parse_condition(scenario_dict[TFields.CONDITION])
            self.valid_target = calculate_action_target(
                condition,
                self._template_entities,
                self._template_relationships)
            actions = self._build_actions(scenario_dict[TFields.ACTIONS],
                                          scenario_id)
            subgraphs = SubGraphBuilder.from_condition(
                condition,
                self._extract_var_and_update_index)

            scenarios.append(
                Scenario(scenario_id, self._template_schema.version(),
                         condition, actions, subgraphs,
                         self.entities, self.relationships))

        return scenarios

    @classmethod
    def build_equivalent_scenario(cls, scenario, template_id, entity_props):
        entities = scenario.entities.copy()
        entities[template_id] = Vertex(
            vertex_id=entities[template_id].vertex_id,
            properties={k: v for k, v in entity_props})
        relationships = {
            rel_id: _build_equivalent_relationship(rel,
                                                   template_id,
                                                   entity_props)
            for rel_id, rel in scenario.relationships.items()}

        def extract_var(symbol_name):
            if symbol_name in entities:
                return entities[symbol_name], ENTITY
            elif symbol_name in relationships:
                return relationships[symbol_name], RELATIONSHIP
            else:
                raise VitrageError('invalid symbol name: {}'
                                   .format(symbol_name))

        subgraphs = SubGraphBuilder.from_condition(
            scenario.condition, extract_var)

        return Scenario(id=scenario.id + '_equivalence',
                        version=scenario.version,
                        condition=scenario.condition,
                        actions=scenario.actions,
                        subgraphs=subgraphs,
                        entities=entities,
                        relationships=relationships)

    def _build_actions(self, actions_def, scenario_id):
        actions = []

        for counter, action_def in enumerate(actions_def):
            action_id = '%s-action%s' % (scenario_id, counter)
            action_type = action_def[TFields.ACTION][TFields.ACTION_TYPE]
            action_loader = self._template_schema.loaders.get(action_type)

            if action_loader:
                actions.append(action_loader.load(action_id, self.valid_target,
                                                  action_def))
            else:
                LOG.warning('Failed to load action of type %s', action_type)

        return actions

    def _extract_var_and_update_index(self, symbol_name):
        if symbol_name in self._template_relationships:
            relationship = self._template_relationships[symbol_name]
            self.relationships[symbol_name] = relationship
            self.entities.update({
                relationship.edge.source_id: relationship.source,
                relationship.edge.target_id: relationship.target
            })
            return relationship, RELATIONSHIP

        entity = self._template_entities[symbol_name]
        self.entities[symbol_name] = entity
        return entity, ENTITY


def calculate_action_target(condition, entities, relationships):
    """Return a vertex that can be used as an action target.

    External actions like execute_mistral do not have an explicit
    action target. This parameter is a must for the sub-graph matching
    algorithm. If it is missing, we would like to select an arbitrary
    target from the condition.
    If the target result is empty the condition is not valid.

    """
    definition_index = entities.copy()
    definition_index.update(relationships)
    targets = get_condition_common_targets(
        condition,
        definition_index,
        TemplateDataSymbolResolver())
    return {TFields.TARGET: targets.pop()} if targets else None


class TemplateDataSymbolResolver(SymbolResolver):
    def is_relationship(self, symbol):
        return isinstance(symbol, EdgeDescription)

    def get_relationship_source_id(self, relationship):
        return relationship.source.vertex_id

    def get_relationship_target_id(self, relationship):
        return relationship.target.vertex_id

    def get_entity_id(self, entity):
        return entity.vertex_id


def _build_equivalent_relationship(relationship,
                                   template_id,
                                   entity_props):
    source = relationship.source
    target = relationship.target
    if relationship.edge.source_id == template_id:
        source = Vertex(vertex_id=source.vertex_id,
                        properties={k: v for k, v in entity_props})
    elif relationship.edge.target_id == template_id:
        target = Vertex(vertex_id=target.vertex_id,
                        properties={k: v for k, v in entity_props})
    return EdgeDescription(source=source,
                           target=target,
                           edge=relationship.edge)
