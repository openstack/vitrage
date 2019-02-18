# Copyright 2018 - Nokia
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

from vitrage.common.constants import TemplateTypes
from vitrage.evaluator.template_fields import TemplateFields
from vitrage.evaluator.template_validation.content.base import \
    get_content_correct_result
from vitrage.evaluator.template_validation.content.base import \
    get_content_fault_result
from vitrage.evaluator.template_validation.status_messages import status_msgs

LOG = log.getLogger(__name__)


class MetadataValidator(object):

    @classmethod
    def validate(cls, metadata):
        if not metadata:
            return get_content_fault_result(62)

        type = metadata.get(TemplateFields.TYPE)

        if not type:
            LOG.error('%s status code: %s' % (status_msgs[64], 64))
            return get_content_fault_result(64)

        if type not in TemplateTypes.types():
            LOG.error('%s status code: %s' % (status_msgs[65], 65))
            return get_content_fault_result(65)

        return get_content_correct_result()
