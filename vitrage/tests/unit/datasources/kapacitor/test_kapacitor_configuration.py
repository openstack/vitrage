# Copyright 2019 - Viettel
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

from oslo_config import cfg

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.datasources.kapacitor.config import KapacitorConfig
from vitrage.datasources.kapacitor import KAPACITOR_DATASOURCE
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.tests import base
from vitrage.tests.mocks import utils


class TestKapacitorConfig(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.TRANSFORMER,
                   default='vitrage.datasources.kapacitor.transformer.'
                           'KapacitorTransformer',
                   help='Kapacitor data source transformer class path',
                   required=True),
        cfg.StrOpt(DSOpts.DRIVER,
                   default='vitrage.datasources.kapacitor.driver.'
                           'KapacitorDriver',
                   help='Kapacitor driver class path',
                   required=True),
        cfg.StrOpt(DSOpts.CONFIG_FILE,
                   help='Kapacitor configuration file',
                   default=utils.get_resources_dir()
                        + '/kapacitor/kapacitor_conf.yaml'),
    ]

    def setUp(self):
        super(TestKapacitorConfig, self).setUp()
        self.conf_reregister_opts(self.OPTS, group=KAPACITOR_DATASOURCE)

    def test_get_vitrage_resource(self):
        """Test the resource returned after processing a list of mappings

        :return:
        """
        # Action
        kapacitor_conf = KapacitorConfig()

        # Test assertions
        mapped_resource = kapacitor_conf.get_vitrage_resource(None)
        self.assertIsNone(mapped_resource, 'expected None')

        mapped_resource = kapacitor_conf.get_vitrage_resource('')
        self.assertIsNone(mapped_resource, 'expected None')

        mapped_resource = kapacitor_conf.get_vitrage_resource('cloud.compute1')
        self.assertIsNotNone(mapped_resource, 'expected Not None')
        self.assertEqual(NOVA_HOST_DATASOURCE, mapped_resource[0])
        self.assertEqual('compute-1', mapped_resource[1])

        mapped_resource = kapacitor_conf.get_vitrage_resource('compute-2')
        self.assertIsNotNone(mapped_resource, 'expected Not None')
        self.assertEqual(NOVA_HOST_DATASOURCE, mapped_resource[0])
        self.assertEqual('compute-2', mapped_resource[1])

        mapped_resource = kapacitor_conf.get_vitrage_resource('instance-1')
        self.assertIsNotNone(mapped_resource, 'expected Not None')
        self.assertEqual(NOVA_INSTANCE_DATASOURCE, mapped_resource[0])
        self.assertEqual('instance-1', mapped_resource[1])

    @staticmethod
    def _assert_equals(mapping1, mapping2):
        return mapping1.kapacitor_host_regexp.pattern == \
            mapping2.kapacitor_host_regexp.pattern and \
            mapping1.resource_type == mapping2.resource_type and \
            mapping1.resource_name == mapping2.resource_name
