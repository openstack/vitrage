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
from oslo_log import log as logging

from vitrage.common.constants import NotifierEventTypes
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources import NOVA_HOST_DATASOURCE
from vitrage.datasources import NOVA_INSTANCE_DATASOURCE
from vitrage.notifier.plugins.base import NotifierBase
from vitrage.notifier.plugins.nova import InstanceState
from vitrage import os_clients

LOG = logging.getLogger(__name__)


class NovaNotifier(NotifierBase):

    @staticmethod
    def get_notifier_name():
        return 'nova'

    def __init__(self):
        super(NovaNotifier, self).__init__()
        self.client = os_clients.nova_client()
        self.actions = {
            NOVA_HOST_DATASOURCE: self._mark_host_down,
            NOVA_INSTANCE_DATASOURCE: self._reset_instance_state
        }

    def process_event(self, data, event_type):
        if not data or not event_type:
            return

        if event_type == NotifierEventTypes.ACTIVATE_MARK_DOWN_EVENT or \
                event_type == NotifierEventTypes.DEACTIVATE_MARK_DOWN_EVENT:

            is_down = event_type == NotifierEventTypes.ACTIVATE_MARK_DOWN_EVENT
            action = self.actions.get(data.get(VProps.VITRAGE_TYPE))

            if action:
                action(data.get(VProps.ID), is_down)
            else:
                LOG.warning('Unsupported datasource type %s for mark_down '
                            'action', data.get(VProps.VITRAGE_TYPE))

    def _mark_host_down(self, host_id, is_down):
        try:
            LOG.info('Nova services.force_down - host id: %s, is_down: %s',
                     host_id, is_down)
            response = self.client.services.force_down(
                host_id, 'nova-compute', is_down)
            LOG.info('RESPONSE %s', response.to_dict())
        except Exception:
            LOG.exception('Failed to services.force_down.')

    def _reset_instance_state(self, server_id, is_down):
        state = InstanceState.ERROR if is_down else InstanceState.ACTIVE
        try:
            LOG.info('Nova servers.reset_state - server: %s, state: %s',
                     server_id, state)
            response = self.client.servers.reset_state(server_id, state)
            LOG.info('RESPONSE %s', response)
        except Exception:
            LOG.exception('Failed to execute servers.reset_state.')
