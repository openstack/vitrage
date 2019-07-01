#  Copyright 2019 - Nokia Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from operator import itemgetter

from oslo_log import log
import pecan

from pecan.core import abort
from vitrage.api.controllers.rest import RootRestController
from vitrage.api.policy import enforce

LOG = log.getLogger(__name__)


# noinspection PyBroadException
class ServiceController(RootRestController):
    @pecan.expose('json')
    def index(self):
        return self.get()

    @pecan.expose('json')
    def get(self):
        enforce("get service list", pecan.request.headers,
                pecan.request.enforcer, {})

        LOG.info('received get service list')

        coordinator = pecan.request.coordinator
        if not coordinator.backend_url:
            abort(500, 'Service API not supported')
        if not coordinator.is_active():
            abort(500, 'Failed to connect to coordination backend')

        try:
            return sorted(coordinator.get_services(), key=itemgetter('name'))
        except Exception:
            LOG.exception('failed to get service list.')
            abort(404, 'Failed to get service list.')
