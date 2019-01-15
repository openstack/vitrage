#  Copyright 2019 - Nokia Corporation
#  #
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#  #
#       http://www.apache.org/licenses/LICENSE-2.0
#  #
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
from oslo_log import log

from vitrage.common.constants import NotifierEventTypes
from vitrage.notifier.plugins.base import NotifierBase
from vitrage import os_clients


LOG = log.getLogger(__name__)


class ZaqarNotifier(NotifierBase):

    def __init__(self, conf):
        super(ZaqarNotifier, self).__init__(conf)
        client = os_clients.zaqar_client(self.conf)
        self._queue = client.queue(self.conf.zaqar.queue)

    @staticmethod
    def get_notifier_name():
        return 'zaqar'

    def process_event(self, data, event_type):
        if event_type in NotifierEventTypes.ALARMS:
            try:
                self._queue.post(data)
            except Exception:
                LOG.exception('Failed to post message to zaqar')
