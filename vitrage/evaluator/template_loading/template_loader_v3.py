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
import copy

from oslo_log import log
import re

from vitrage.evaluator.condition import parse_condition
from vitrage.evaluator.template_data import EdgeDescription
from vitrage.evaluator.template_data import ENTITY
from vitrage.evaluator.template_data import RELATIONSHIP
from vitrage.evaluator.template_data import Scenario
from vitrage.evaluator.template_data import TemplateData
from vitrage.evaluator.template_fields import TemplateFields as TFields
from vitrage.evaluator.template_loading.props_converter import PropsConverter
from vitrage.evaluator.template_loading.scenario_loader import \
    calculate_action_target
from vitrage.evaluator.template_loading.subgraph_builder import SubGraphBuilder
from vitrage.evaluator.template_validation.base import ValidationError
from vitrage.graph import Edge
from vitrage.graph import Vertex


LOG = log.getLogger(__name__)


class TemplateLoader(object):

    def load(self, template_schema, template_def, def_templates=None):
        template = copy.deepcopy(template_def)
        entities = _build_entities(template)
        relationships = _build_condition_relationships(template, entities)
        return TemplateData(scenarios=_build_scenarios(
            template, entities, relationships, template_schema))


def _build_entities(template):
    entities = dict()
    for template_id, entity in template[TFields.ENTITIES].items():
        properties = PropsConverter.convert_props_with_dictionary(entity)
        entities[template_id] = Vertex(template_id, properties)
    return entities


def _build_condition_relationships(template, entities):
    relationships = dict()
    for scenario in template[TFields.SCENARIOS]:
        condition = scenario.get(TFields.CONDITION)
        extracted_relationships, processed_condition = \
            _process_condition(condition, entities)
        relationships.update(extracted_relationships)
        scenario[TFields.CONDITION] = processed_condition

    return relationships


def _process_condition(condition, entities):
    """Process the condition, while extracting the condition relationships

    Example:
    condition: 'host_alarm [ on ] host AND host [contains] instance'

    regex matches:
    match group 1: 'host_alarm'
    match group 2: 'on'
    match group 3: 'host'
    ..

    Example returns:
    processed_condition: 'host_alarm__on__host AND host__contains__instance'
    extracted_relationships: {
       host_alarm__on__host: EdgeDescription(...),
       host__contains__instance: EdgeDescription(...),
       }
    """
    regex = r"(\w+)\s*\[\s*(\w+)\s*\]\s*(\w+)"
    extracted_relationships = dict()

    def relation_str(matchobj):
        source = matchobj.group(1)
        label = matchobj.group(2)
        target = matchobj.group(3)
        relation_id = '%s__%s__%s' % (source, label, target)
        extracted_relationships[relation_id] = EdgeDescription(
            Edge(source, target, label, dict()),
            entities[source],
            entities[target])
        return relation_id

    processed_condition = re.sub(regex, relation_str, condition)
    return extracted_relationships, processed_condition


def _build_scenarios(template, entities, relationships, schema):
    name = template[TFields.METADATA][TFields.NAME]

    scenarios = []
    for index, scenario in enumerate(template[TFields.SCENARIOS]):
        s_id = "%s-scenario%d" % (name, index)
        condition = parse_condition(scenario.get(TFields.CONDITION))
        default_target = calculate_action_target(condition,
                                                 entities,
                                                 relationships)

        if not default_target:
            raise ValidationError(135, 'scenario %d' % index,
                                  scenario.get(TFields.CONDITION))

        tmp_scenario = Scenario(
            id=s_id,
            version=schema.version(),
            condition=None,
            actions=_build_actions(schema, scenario, s_id, default_target),
            subgraphs=_build_subgraphs(condition, entities, relationships),
            entities=entities,
            relationships=relationships)
        scenarios.append(tmp_scenario)
    return scenarios


def _build_actions(template_schema, scenario, scenario_id, default_target):
    actions = []
    actions_def = scenario[TFields.ACTIONS]
    for counter, action_def in enumerate(actions_def):
        action_id = '%s-action%d' % (scenario_id, counter)
        action_type, action_props = action_def.popitem()
        action = template_schema.loaders.get(action_type).load(
            action_id,
            default_target,
            action_props,
            action_type
        )
        actions.append(action)
    return actions


def _build_subgraphs(condition, entities, relationships):

    def _extract_var(symbol_name):
        if symbol_name in relationships:
            edge_descriptor = relationships[symbol_name]
            return edge_descriptor, RELATIONSHIP
        elif symbol_name in entities:
            vertex = entities[symbol_name]
            return vertex, ENTITY

    return SubGraphBuilder.from_condition(condition, _extract_var)
