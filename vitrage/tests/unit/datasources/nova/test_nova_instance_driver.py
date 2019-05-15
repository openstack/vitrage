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

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import UpdateMethod
from vitrage.datasources.nova.instance.driver import InstanceDriver
from vitrage.tests import base
from vitrage.tests.mocks import mock_driver as mock_sync

LOG = logging.getLogger(__name__)


# noinspection PyProtectedMember
class NovaHostTransformerTest(base.BaseTest):

    OPTS = [
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH),
    ]

    def test_use_versioned_notifications(self):
        LOG.debug('Nova instance driver test')

        # Test setup
        driver = InstanceDriver()
        self.cfg_fixture.config(
            use_nova_versioned_notifications=True)
        update_versioned_event, update_legacy_event = self._create_events()

        # Test action
        events = driver.enrich_event(update_versioned_event,
                                     'instance.create.end')
        self.assert_is_not_empty(events)

        # Test action
        events = driver.enrich_event(update_legacy_event,
                                     'compute.instance.create.end')
        self.assert_is_empty(events)

    def test_use_legacy_notifications(self):
        LOG.debug('Nova instance driver test')

        # Test setup
        driver = InstanceDriver()
        self.cfg_fixture.config(
            use_nova_versioned_notifications=False)
        update_versioned_event, update_legacy_event = self._create_events()

        # Test action
        events = driver.enrich_event(update_versioned_event,
                                     'instance.create.end')
        self.assert_is_empty(events)

        # Test action
        events = driver.enrich_event(update_legacy_event,
                                     'compute.instance.create.end')
        self.assert_is_not_empty(events)

    @staticmethod
    def _create_events():
        spec_list = mock_sync.simple_instance_generators(
            host_num=1, vm_num=1, update_events=1,
            use_nova_versioned_format=True
        )
        update_versioned_event = \
            mock_sync.generate_random_events_list(spec_list)[0]

        spec_list = mock_sync.simple_instance_generators(
            host_num=1, vm_num=1, update_events=1,
            use_nova_versioned_format=False
        )
        update_legacy_event = \
            mock_sync.generate_random_events_list(spec_list)[0]

        return update_versioned_event, update_legacy_event
