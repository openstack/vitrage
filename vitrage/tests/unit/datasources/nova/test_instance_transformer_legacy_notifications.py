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

from oslo_config import cfg
from oslo_log import log as logging

from vitrage.tests.mocks import mock_driver as mock_sync
from vitrage.tests.unit.datasources.nova.base_nova_instance_transformer \
    import BaseNovaInstanceTransformerTest

LOG = logging.getLogger(__name__)


# noinspection PyProtectedMember
class NovaInstanceTransformerLegacyNotifTest(
        BaseNovaInstanceTransformerTest):

    DEFAULT_GROUP_OPTS = [
        cfg.BoolOpt('use_nova_versioned_notifications',
                    default=False),
    ]

    def setUp(self):
        super(NovaInstanceTransformerLegacyNotifTest, self).setUp()
        self.cfg_fixture.config(
            use_nova_versioned_notifications=False)

    def test_update_event_transform(self):
        LOG.debug('Test actual transform action for update events')

        # Test setup
        spec_list = mock_sync.simple_instance_generators(
            host_num=1, vm_num=1, update_events=10,
            use_nova_versioned_format=False
        )
        instance_events = mock_sync.generate_random_events_list(spec_list)

        self._test_update_event_transform(instance_events)

    def test_create_placeholder_vertex(self):
        self._test_create_placeholder_vertex()

    def test_create_entity_key(self):
        self._test_create_entity_key()

    def test_build_instance_key(self):
        self._test_build_instance_key()

    @classmethod
    def _get_default_group_opts(cls):
        return cls.DEFAULT_GROUP_OPTS
