# Copyright 2018 - Nokia Corporation
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
import pecan

from oslo_log import log
from oslo_utils.strutils import bool_from_string
from osprofiler import profiler
from pecan.core import abort

from vitrage.api.controllers.rest import RootRestController
from vitrage.api.policy import enforce
from vitrage.common.constants import TenantProps

LOG = log.getLogger(__name__)


# noinspection PyBroadException
@profiler.trace_cls("webhook controller",
                    info={}, hide_args=False, trace_private=False)
class WebhookController(RootRestController):

    @pecan.expose('json')
    def get_all(self, **kwargs):
        LOG.info('list all webhooks with args: %s', kwargs)

        all_tenants = kwargs.get(TenantProps.ALL_TENANTS, False)
        all_tenants = bool_from_string(all_tenants)

        if all_tenants:
            enforce('webhook list:all_tenants', pecan.request.headers,
                    pecan.request.enforcer, {})
        else:
            enforce('webhook list', pecan.request.headers,
                    pecan.request.enforcer, {})

        try:
            return self._get_all(all_tenants)
        except Exception:
            LOG.exception('Failed to list webhooks.')
            abort(404, 'Failed to list webhooks.')

    @staticmethod
    def _get_all(all_tenants):
        webhooks = \
            pecan.request.client.call(pecan.request.context,
                                      'get_all_webhooks',
                                      all_tenants=all_tenants)
        LOG.info(webhooks)
        return webhooks

    @pecan.expose('json')
    def get(self, id):
        LOG.info('Show webhook with id: %s', id)

        enforce('webhook show', pecan.request.headers,
                pecan.request.enforcer, {})

        try:
            return self._get(id)
        except Exception:
            LOG.exception('Failed to get webhook.')
            abort(404, 'Failed to get webhook.')

    @staticmethod
    def _get(id):
        webhook = \
            pecan.request.client.call(pecan.request.context,
                                      'get_webhook',
                                      id=id)
        LOG.info(webhook)
        if not webhook:
            abort(404, "Failed to find webhook with ID: %s" % id)
        return webhook

    @pecan.expose('json')
    def post(self, **kwargs):
        LOG.info("Add webhook with following props: %s" % kwargs)
        enforce('webhook add', pecan.request.headers,
                pecan.request.enforcer, {})
        try:
            return self._post(**kwargs)
        except Exception:
            LOG.exception('Failed to add webhooks.')
            abort(400, 'Failed to add webhooks.')

    @staticmethod
    def _post(**kwargs):
        url = kwargs.get('url')
        if not url:
            abort(400, 'Missing mandatory field: URL')
        regex_filter = kwargs.get('regex_filter', None)
        headers = kwargs.get('headers', None)

        webhook = \
            pecan.request.client.call(pecan.request.context,
                                      'add_webhook',
                                      url=url,
                                      regex_filter=regex_filter,
                                      headers=headers)
        LOG.info(webhook)
        if webhook.get("ERROR"):
            abort(400, "Failed to add webhook: %s" % webhook.get("ERROR"))
        return webhook

    @pecan.expose('json')
    def delete(self, id):

        LOG.info('delete webhook with id: %s', id)
        enforce("webhook delete",
                pecan.request.headers,
                pecan.request.enforcer,
                {})

        try:
            return self._delete_registration(id)
        except Exception:
            LOG.exception('Failed to delete webhook "%s"', id)
            abort(404, 'Failed to delete webhook.')

    @staticmethod
    def _delete_registration(id):
        resource = pecan.request.client.call(
            pecan.request.context,
            'delete_webhook',
            id=id)
        if not resource:
            abort(404, "Failed to find resource with ID: %s" % id)
        LOG.info("Request returned with: %s" % resource)
        return resource
