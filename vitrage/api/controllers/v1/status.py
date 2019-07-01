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

import oslo_messaging
import pecan
from pecan import rest
from vitrage.api.policy import enforce


class StatusController(rest.RestController):
    @pecan.expose('json')
    def index(self):
        return self.get()

    @pecan.expose('json')
    def get(self):
        enforce("get status", pecan.request.headers,
                pecan.request.enforcer, {})
        try:
            client = pecan.request.client.prepare(timeout=5)
            backend_is_alive = client.call(pecan.request.context, 'is_alive')
            if backend_is_alive:
                return {'reason': 'OK'}
            else:
                pecan.abort(503, detail='vitrage-graph is not ready')
        except oslo_messaging.MessagingTimeout:
            pecan.abort(503, detail='vitrage-graph is not available')
