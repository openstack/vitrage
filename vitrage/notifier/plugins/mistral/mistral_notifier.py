# Copyright 2017 - Nokia
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
from vitrage.evaluator.actions.recipes.execute_mistral import INPUT
from vitrage.evaluator.actions.recipes.execute_mistral import WORKFLOW
from vitrage.notifier.plugins.base import NotifierBase
from vitrage import os_clients


LOG = logging.getLogger(__name__)


class MistralNotifier(NotifierBase):

    def __init__(self):
        super(MistralNotifier, self).__init__()
        self._client = None

    @staticmethod
    def get_notifier_name():
        return 'mistral'

    @staticmethod
    def use_private_topic():
        return True

    @property
    def client(self):
        if not self._client:
            self._client = os_clients.mistral_client()
        return self._client

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        """Mistral Endpoint"""
        LOG.info('Vitrage Event Info: publisher_id %s', publisher_id)
        LOG.info('Vitrage Event Info: event_type %s', event_type)
        LOG.info('Vitrage Event Info: metadata %s', metadata)
        LOG.info('Vitrage Event Info: payload %s', payload)

        self.process_event(payload, event_type)

    def process_event(self, data, event_type):
        if event_type == NotifierEventTypes.EXECUTE_EXTERNAL_ACTION:
            LOG.debug('Going to execute Mistral workflow for: %s', data)

            if WORKFLOW not in data:
                LOG.warning('Failed to execute a Mistral workflow without '
                            'a workflow name')
                return

            try:
                workflow = data[WORKFLOW]
                workflow_input = data.get(INPUT, {})

                response = self.client.executions.create(
                    workflow_identifier=workflow,
                    workflow_input=workflow_input,
                    wf_params={})

                if response:
                    LOG.debug('Mistral response: %s', response)
                else:
                    LOG.error('Failed to execute Mistral action')

            except Exception:
                LOG.exception('Failed to execute Mistral action.')
