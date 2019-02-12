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
import gc
import oslo_messaging

from oslo_context import context
from oslo_policy import policy
from pecan import hooks

from vitrage.common import policies
from vitrage.coordination import coordination
from vitrage import messaging
from vitrage import rpc as vitrage_rpc
from vitrage import storage


class ConfigHook(hooks.PecanHook):
    """Attach the configuration and policy enforcer object to the request. """

    def __init__(self, conf):
        self.conf = conf
        self.enforcer = policy.Enforcer(conf)
        self._register_rules()

    def _register_rules(self):
        self.enforcer.register_defaults(policies.list_rules())

    def before(self, state):
        state.request.cfg = self.conf
        state.request.enforcer = self.enforcer


class RPCHook(hooks.PecanHook):
    """Create and attach an rpc to the request. """

    def __init__(self, conf):
        transport = messaging.get_rpc_transport(conf)
        target = oslo_messaging.Target(topic=conf.rpc_topic)
        self.client = vitrage_rpc.get_client(transport, target)

    def on_route(self, state):
        state.request.client = self.client


class TranslationHook(hooks.PecanHook):

    def after(self, state):
        # After a request has been done, we need to see if
        # ClientSideError has added an error onto the response.
        # If it has we need to get it info the thread-safe WSGI
        # environ to be used by the ParsableErrorMiddleware.
        if hasattr(state.response, 'translatable_error'):
            state.request.environ['translatable_error'] = (
                state.response.translatable_error)


class ContextHook(hooks.PecanHook):

    def before(self, state):
        user_id = state.request.headers.get('X-User-Id')
        user_id = state.request.headers.get('X-User', user_id)
        user_name = state.request.headers.get('X-User-Name', '')
        tenant_id = state.request.headers.get('X-Project-Id')
        auth_token = state.request.headers.get('X-Auth-Token')
        # TODO(DANY) use roles
        # roles = pecan.request.headers.get('X-Roles', '').split(',')
        # roles = [r.strip() for r in roles]
        ctx = context.RequestContext(auth_token=auth_token, user=user_id,
                                     # roles=roles,
                                     tenant=tenant_id,
                                     is_admin=(user_name == 'admin'))

        # Inject the context...
        state.request.context = ctx.to_dict()


class DBHook(hooks.PecanHook):

    def __init__(self, conf):
        self.storage = storage.get_connection_from_config(conf)

    def before(self, state):
        state.request.storage = self.storage


class GCHook(hooks.PecanHook):

    def after(self, state):
        gc.collect()


class CoordinatorHook(hooks.PecanHook):

    def __init__(self, conf):
        self.coordinator = coordination.Coordinator(conf)
        self.coordinator.start()
        self.coordinator.join_group()

    def before(self, state):
        state.request.coordinator = self.coordinator
