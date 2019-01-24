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

from vitrage.evaluator.template_data import EdgeDescription
from vitrage.evaluator.template_data import TemplateData
from vitrage.evaluator.template_fields import TemplateFields as TFields
from vitrage.evaluator.template_loading.props_converter import PropsConverter
from vitrage.evaluator.template_loading.scenario_loader import ScenarioLoader
from vitrage.graph import Edge
from vitrage.graph import Vertex
from vitrage.utils import evaluator as evaluator_utils


LOG = log.getLogger(__name__)


class TemplateLoader(object):

    def __init__(self):
        self.entities = {}
        self.relationships = {}

    def load(self, template_schema, template_def, def_templates=None):

        name = template_def[TFields.METADATA][TFields.NAME]

        # template_type might be None, it is defined only in version 2
        template_type = template_def[TFields.METADATA].get(TFields.TYPE)

        if def_templates is None:
            def_templates = {}
        defs = {}

        if TFields.DEFINITIONS in template_def:
            defs = template_def[TFields.DEFINITIONS]
            if TFields.ENTITIES in defs:
                self.entities = self._build_entities(defs[TFields.ENTITIES])

        # Add definitions from template then from definition templates.
        if TFields.INCLUDES in template_def:
            includes = template_def[TFields.INCLUDES]
            self._build_entities_from_def_templates(
                includes, def_templates, self.entities)

        if TFields.RELATIONSHIPS in defs:
            self.relationships = self._build_relationships(
                defs[TFields.RELATIONSHIPS])

        if TFields.INCLUDES in template_def:
            includes = template_def[TFields.INCLUDES]
            self._build_relationships_with_def_templates(includes,
                                                         def_templates,
                                                         self.relationships)

        scenarios = ScenarioLoader(template_schema, name, self.entities,
                                   self.relationships).\
            build_scenarios(template_def[TFields.SCENARIOS])

        return TemplateData(name, template_type, template_schema.version(),
                            self.entities, self.relationships, scenarios)

    def _build_entities(self, entities_defs):
        entities = {}
        for entity_def in entities_defs:

            entity_dict = entity_def[TFields.ENTITY]
            template_id = entity_dict[TFields.TEMPLATE_ID]
            properties = PropsConverter.convert_props_with_dictionary(
                self._extract_properties(entity_dict))
            entities[template_id] = Vertex(template_id, properties)

        return entities

    def _build_entities_from_def_templates(
            self, includes, def_templates, entities):

        for def_template_dict in includes:

            name = def_template_dict[TFields.NAME]
            def_template = evaluator_utils.find_def_template(
                name, def_templates)
            defs = def_template[TFields.DEFINITIONS]
            entities_defs = defs[TFields.ENTITIES]

            for entity_def in entities_defs:

                entity_dict = entity_def[TFields.ENTITY]
                template_id = entity_dict[TFields.TEMPLATE_ID]
                if template_id not in entities:

                    properties = \
                        PropsConverter.convert_props_with_dictionary(
                            self._extract_properties(entity_dict))
                    entities[template_id] = Vertex(template_id, properties)

    def _build_relationships(self, relationships_defs):

        relationships = {}
        for relationship_def in relationships_defs:

            relationship_dict = relationship_def[TFields.RELATIONSHIP]
            relationship = self._extract_relationship_info(relationship_dict)
            template_id = relationship_dict[TFields.TEMPLATE_ID]
            relationships[template_id] = relationship

        return relationships

    def _build_relationships_with_def_templates(
            self, includes, def_templates, relationships):

        for def_template_dict in includes:

            name = def_template_dict[TFields.NAME]
            def_template = evaluator_utils.find_def_template(
                name, def_templates)

            if TFields.RELATIONSHIPS in def_template[TFields.DEFINITIONS]:
                defs = def_template[TFields.DEFINITIONS]
                relationship_defs = defs[TFields.RELATIONSHIPS]

                for relationship_def in relationship_defs:
                    relationship_dict = relationship_def[TFields.RELATIONSHIP]
                    template_id = relationship_dict[TFields.TEMPLATE_ID]

                    if template_id not in relationships:
                        relationship = self._extract_relationship_info(
                            relationship_dict)
                        relationships[template_id] = relationship

    def _extract_relationship_info(self, relationship_dict):
        source_id = relationship_dict[TFields.SOURCE]
        target_id = relationship_dict[TFields.TARGET]

        edge = Edge(source_id,
                    target_id,
                    relationship_dict[TFields.RELATIONSHIP_TYPE],
                    self._extract_properties(relationship_dict))

        source = self.entities[source_id]
        target = self.entities[target_id]
        return EdgeDescription(edge, source, target)

    @staticmethod
    def _extract_properties(var_dict):

        ignore_ids = [TFields.TEMPLATE_ID, TFields.SOURCE, TFields.TARGET]
        return \
            {key: var_dict[key] for key in var_dict if key not in ignore_ids}
