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

import oslo_messaging
import pecan
from pecan import rest


class RootRestController(rest.RestController):

    @pecan.expose()
    def _route(self, args, request=None):
        """All requests go through here

        We can check the backend status
        """

        if not pecan.request.check_backend:
            return super(RootRestController, self)._route(args, request)

        try:
            client = pecan.request.client.prepare(timeout=5)
            backend_is_alive = client.call(pecan.request.context, 'is_alive')
            if backend_is_alive:
                return super(RootRestController, self)._route(args, request)
            else:
                pecan.abort(503, detail='vitrage-graph is not ready')
        except oslo_messaging.MessagingTimeout:
            pecan.abort(503, detail='vitrage-graph not available')
