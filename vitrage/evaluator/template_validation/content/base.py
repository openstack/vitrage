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

import abc

from oslo_log import log
from vitrage.evaluator.template_fields import TemplateFields
from vitrage.evaluator.template_schema_factory import TemplateSchemaFactory
from vitrage.evaluator.template_validation.base import get_correct_result
from vitrage.evaluator.template_validation.base import get_fault_result
from vitrage.evaluator.template_validation.base import get_warning_result
from vitrage.evaluator.template_validation.status_messages import status_msgs


LOG = log.getLogger(__name__)
RESULT_DESCRIPTION = 'Template content validation'


def get_content_correct_result():
    return get_correct_result(RESULT_DESCRIPTION)


def get_content_fault_result(code, msg=None):
    return get_fault_result(RESULT_DESCRIPTION, code, msg)


def get_content_warning_result(code):
    return get_warning_result(RESULT_DESCRIPTION, code)


def validate_template_id(definitions_index, id_to_check):
    if id_to_check not in definitions_index:
        msg = status_msgs[3] + ' template id: %s' % id_to_check
        LOG.error('%s status code: %s' % (msg, 3))
        return get_fault_result(RESULT_DESCRIPTION, 3, msg)

    return get_correct_result(RESULT_DESCRIPTION)


def get_template_schema(template):
    metadata = template.get(TemplateFields.METADATA)

    if metadata is None:
        LOG.error('%s status code: %s' % (status_msgs[62], 62))
        return get_content_fault_result(62), None

    version = metadata.get(TemplateFields.VERSION)
    template_schema = TemplateSchemaFactory().template_schema(version)

    if template_schema:
        return get_content_correct_result(), template_schema
    else:
        LOG.error('%s status code: %s' % (status_msgs[63], 63))
        return get_content_fault_result(63), None


class ActionValidator(object, metaclass=abc.ABCMeta):

    @staticmethod
    @abc.abstractmethod
    def validate(action, definitions_index):
        """Validate the content of the action.

        :param action: The action to be validated
        :type action: dict

        :param definitions_index: Entities and relationships in the template
        :type definitions_index: dict

        """
        pass
