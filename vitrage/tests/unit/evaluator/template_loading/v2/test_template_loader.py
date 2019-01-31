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

from vitrage.common.constants import TemplateTypes
from vitrage.tests import base
from vitrage.tests.mocks import utils
from vitrage.tests.unit.evaluator import get_template_data
from vitrage.utils import file as file_utils


class TemplateLoaderTest(base.BaseTest):

    STANDARD_TEMPLATE = 'v2_standard.yaml'

    def test_standard_template(self):
        template_path = '%s/templates/version/v2/%s' % \
                        (utils.get_resources_dir(), self.STANDARD_TEMPLATE)
        template_definition = file_utils.load_yaml_file(template_path, True)

        template_data = get_template_data(template_definition)
        self.assertIsNotNone(template_data)

        template_type = template_data.template_type
        self.assertIsNotNone(template_type, 'v2 template must include a type')
        self.assertEqual(TemplateTypes.STANDARD, template_type,
                         'template_type should be ' + TemplateTypes.STANDARD)
