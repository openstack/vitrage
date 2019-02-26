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
import re

from vitrage.evaluator.template_fields import TemplateFields
from vitrage.evaluator.template_validation.content.base import \
    get_content_correct_result
from vitrage.evaluator.template_validation.content.base import \
    get_content_fault_result
from vitrage.evaluator.template_validation.content.base import \
    validate_template_id
from vitrage.evaluator.template_validation.status_messages import status_msgs
from vitrage.utils import evaluator as evaluator_utils

LOG = log.getLogger(__name__)


class DefinitionsValidator(object):

    @classmethod
    def def_template_content_validation(cls, def_template):
        def_template_definitions = def_template[TemplateFields.DEFINITIONS]

        entities_index = {}
        entities = def_template_definitions[TemplateFields.ENTITIES]
        result = cls.validate_entities_definition(entities, entities_index)

        relationships_index = {}

        if result.is_valid_config \
                and TemplateFields.RELATIONSHIPS in def_template_definitions:
            relationships = \
                def_template_definitions[TemplateFields.RELATIONSHIPS]
            result = \
                cls.validate_relationships_definitions(relationships,
                                                       relationships_index,
                                                       entities_index)

        return result

    @classmethod
    def validate_entities_definition(cls, entities, entities_index):
        for entity in entities:
            entity_dict = entity[TemplateFields.ENTITY]
            result = \
                cls._validate_entity_definition(entity_dict, entities_index)

            if not result.is_valid_config:
                return result

            entities_index[entity_dict[TemplateFields.TEMPLATE_ID]] = \
                entity_dict

        return get_content_correct_result()

    @classmethod
    def validate_definitions_with_includes(
            cls, template_includes, def_templates, entities_index):

        for include in template_includes:

            name = include[TemplateFields.NAME]
            def_template = \
                evaluator_utils.find_def_template(name, def_templates)

            if not def_template:

                LOG.error('%s status code: %s' % (status_msgs[142], 142))
                return get_content_fault_result(142)

            def_template_definitions = def_template[TemplateFields.DEFINITIONS]
            def_template_entities = \
                def_template_definitions[TemplateFields.ENTITIES]
            result = cls._validate_include_entities_definition(
                def_template_entities, entities_index)

            if not result.is_valid_config:
                return result

        return get_content_correct_result()

    @classmethod
    def validate_relationships_definitions(cls,
                                           relationships,
                                           relationships_index,
                                           entities_index):
        for relationship in relationships:

            relationship_dict = relationship[TemplateFields.RELATIONSHIP]
            result = cls._validate_relationship(relationship_dict,
                                                relationships_index,
                                                entities_index)
            if not result.is_valid_config:
                return result

            template_id = relationship_dict[TemplateFields.TEMPLATE_ID]
            relationships_index[template_id] = relationship_dict
        return get_content_correct_result()

    @classmethod
    def validate_relationships_definitions_with_includes(cls,
                                                         template_includes,
                                                         def_templates,
                                                         entities_index,
                                                         relationships_index):

        for include in template_includes:

            name = include[TemplateFields.NAME]
            def_template = \
                evaluator_utils.find_def_template(name, def_templates)

            if def_template:
                defs = def_template[TemplateFields.DEFINITIONS]
                relationships = defs[TemplateFields.RELATIONSHIPS]

                for relationship in relationships:
                    relationship_dict = \
                        relationship[TemplateFields.RELATIONSHIP]
                    template_id = relationship_dict[TemplateFields.TEMPLATE_ID]
                    if template_id not in relationships_index:
                        result = cls._validate_def_template_relationship(
                            relationship_dict,
                            entities_index)

                        if not result.is_valid_config:
                            return result

                        relationships_index[template_id] = relationship_dict

        return get_content_correct_result()

    # noinspection PyBroadException
    @classmethod
    def _validate_entity_definition(cls, entity_dict, entities_index):
        template_id = entity_dict[TemplateFields.TEMPLATE_ID]
        if template_id in entities_index:
            LOG.error('%s status code: %s' % (status_msgs[2], 2))
            return get_content_fault_result(2)

        for key, value in entity_dict.items():

            if key.lower().endswith(TemplateFields.REGEX):
                try:
                    re.compile(value)
                except Exception:
                    LOG.error('%s %s status code: %s' % (status_msgs[47],
                                                         key, 47))
                    return get_content_fault_result(47)

        return get_content_correct_result()

    @classmethod
    def _validate_include_entities_definition(
            cls,
            def_template_entities,
            entities_index):

        for entity in def_template_entities:
            entity_dict = entity[TemplateFields.ENTITY]
            result = \
                cls._validate_entity_definition(entity_dict, entities_index)

            if not result.is_valid_config:
                return result

            if entity_dict[TemplateFields.TEMPLATE_ID] not in entities_index:
                template_id = entity_dict[TemplateFields.TEMPLATE_ID]
                entities_index[template_id] = entity_dict

        return get_content_correct_result()

    @classmethod
    def _validate_def_template_relationship(cls, relationship, entities_index):
        target = relationship[TemplateFields.TARGET]
        result = validate_template_id(entities_index, target)

        if result.is_valid_config:
            source = relationship[TemplateFields.SOURCE]
            result = validate_template_id(entities_index, source)

        return result

    @classmethod
    def _validate_relationship(cls,
                               relationship,
                               relationships_index,
                               entities_index):

        template_id = relationship[TemplateFields.TEMPLATE_ID]
        if template_id in relationships_index or template_id in entities_index:
            LOG.error('%s status code: %s' % (status_msgs[2], 2))
            return get_content_fault_result(2)

        target = relationship[TemplateFields.TARGET]
        result = validate_template_id(entities_index, target)

        if result.is_valid_config:
            source = relationship[TemplateFields.SOURCE]
            result = validate_template_id(entities_index, source)

        return result
