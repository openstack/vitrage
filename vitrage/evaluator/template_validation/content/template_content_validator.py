# Copyright 2016 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_log import log

from vitrage.evaluator.template_fields import TemplateFields
from vitrage.evaluator.template_functions import GET_PARAM
from vitrage.evaluator.template_validation.content.base import \
    get_template_schema

LOG = log.getLogger(__name__)


def content_validation(template, def_templates=None, params=None):

    if def_templates is None:
        def_templates = {}

    entities_index = {}
    template_definitions = {}

    result, template_schema = get_template_schema(template)

    # Validate metadata
    metadata_validator = \
        template_schema.validators.get(TemplateFields.METADATA) \
        if result.is_valid_config and template_schema else None

    if result.is_valid_config:
        if metadata_validator:
            metadata = template.get(TemplateFields.METADATA)
            result = metadata_validator.validate(metadata)
        else:
            result.is_valid_config = False  # Not supposed to happen

    # Validate parameters
    if result.is_valid_config:
        result = parameters_validation(template_schema, template, params)

    # Validate definitions
    def_validator = \
        template_schema.validators.get(TemplateFields.DEFINITIONS) \
        if result.is_valid_config and template_schema else None

    if result.is_valid_config and not def_validator:
        result.is_valid_config = False  # Not supposed to happen

    if result.is_valid_config and TemplateFields.DEFINITIONS in template:
        template_definitions = template[TemplateFields.DEFINITIONS]

        if TemplateFields.ENTITIES in template_definitions:
            entities = template_definitions[TemplateFields.ENTITIES]
            result = def_validator.validate_entities_definition(entities,
                                                                entities_index)

    # If there are duplicate definitions in several includes under the same
    # name, will regard the first one
    if result.is_valid_config and TemplateFields.INCLUDES in template:
        template_includes = template[TemplateFields.INCLUDES]
        result = \
            def_validator.validate_definitions_with_includes(template_includes,
                                                             def_templates,
                                                             entities_index)

    relationship_index = {}

    if result.is_valid_config and \
            TemplateFields.RELATIONSHIPS in template_definitions:
        relationships = template_definitions[TemplateFields.RELATIONSHIPS]
        result = def_validator.validate_relationships_definitions(
            relationships, relationship_index, entities_index)

    if result.is_valid_config and TemplateFields.INCLUDES in template:
        template_includes = template[TemplateFields.INCLUDES]
        result = \
            def_validator.validate_relationships_definitions_with_includes(
                template_includes,
                def_templates,
                entities_index,
                relationship_index)

    # Validate scenarios
    if result.is_valid_config:
        scenario_validator = template_schema.validators.get(
            TemplateFields.SCENARIOS)
        scenarios = template[TemplateFields.SCENARIOS]
        definitions_index = entities_index.copy()
        definitions_index.update(relationship_index)
        result = scenario_validator.validate(template_schema,
                                             definitions_index, scenarios)

    return result


def parameters_validation(template_schema, template, actual_params):
    params_validator = template_schema.validators[GET_PARAM]
    return params_validator.validate(template, actual_params)
