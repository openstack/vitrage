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
import ast
import re

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

import requests

from vitrage.common.constants import NotifierEventTypes
from vitrage.common.constants import VertexProperties as VProps
from vitrage.notifier.plugins.base import NotifierBase
from vitrage.notifier.plugins.webhook import utils as webhook_utils
from vitrage import storage

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
URL = 'url'
IS_ADMIN_WEBHOOK = 'is_admin_webhook'
NOTIFICATION_TYPE = 'notification_type'
NOTIFICATION = 'notification'
PAYLOAD = 'payload'
ALARM_FILTER = (NOTIFICATION,
                PAYLOAD,
                VProps.VITRAGE_ID,
                VProps.ID,
                VProps.RESOURCE,
                VProps.NAME,
                VProps.UPDATE_TIMESTAMP,
                VProps.VITRAGE_OPERATIONAL_STATE,
                VProps.VITRAGE_TYPE,
                VProps.PROJECT_ID,
                VProps.UPDATE_TIMESTAMP,
                VProps.VITRAGE_CATEGORY,
                VProps.STATE,
                VProps.VITRAGE_OPERATIONAL_SEVERITY)
RESOURCE_FILTER = (VProps.VITRAGE_ID,
                   VProps.ID,
                   VProps.RESOURCE,
                   VProps.NAME,
                   VProps.VITRAGE_CATEGORY,
                   VProps.UPDATE_TIMESTAMP,
                   VProps.VITRAGE_OPERATIONAL_STATE,
                   VProps.VITRAGE_TYPE,
                   VProps.PROJECT_ID,
                   VProps.UPDATE_TIMESTAMP,
                   VProps.VITRAGE_OPERATIONAL_SEVERITY)


class Webhook(NotifierBase):

    @staticmethod
    def get_notifier_name():
        return 'webhook'

    def __init__(self):
        super(Webhook, self).__init__()
        self._db = storage.get_connection_from_config()
        self.max_retries = CONF.webhook.max_retries
        self.default_headers = {'content-type': 'application/json'}

    def process_event(self, data, event_type):

        if event_type in NotifierEventTypes.ALARMS:

            LOG.info('Webhook notifier started processing %s', data)

            webhooks = self._load_webhooks()

            LOG.debug('There are %d registered webhooks', len(webhooks))

            if webhooks:
                for webhook in webhooks:
                    webhook_filters = self._get_webhook_filters(webhook)
                    data = self._filter_fields(data)

                    LOG.debug('webhook_filter: %s, filtered data: %s',
                              webhook_filters, data)

                    if self._check_against_filter(webhook_filters, data)\
                            and self._check_correct_tenant(webhook, data):
                        LOG.info('Going to post data to webhook %s', webhook)
                        self._post_data(webhook, event_type, data)

            LOG.info('Webhook notifier finished processing %s', data)

    def _post_data(self, webhook, event_type, data):
        try:
            webhook_data = {'notification': event_type, 'payload': data}
            webhook_headers = self._get_webhook_headers(webhook)
            session = requests.Session()
            session.mount(webhook[URL],
                          requests.adapters.HTTPAdapter(
                              max_retries=self.max_retries))
            resp = session.post(str(webhook[URL]),
                                data=jsonutils.dumps(webhook_data),
                                headers=webhook_headers)
            LOG.info('posted %s to %s. Response status %s, reason %s',
                     webhook_data, webhook[URL],
                     resp.status_code, resp.reason)
        except Exception:
            LOG.exception("Could not post to webhook '%s'", webhook['id'])

    def _load_webhooks(self):
        db_webhooks = self._db.webhooks.query()
        return [webhook_utils.db_row_to_dict(webhook) for webhook in
                db_webhooks]

    def _get_webhook_headers(self, webhook):
        headers = self.default_headers.copy()
        headers['x-openstack-request-id'] = b'req-' + \
                                            uuidutils.generate_uuid().encode(
                                                'ascii')
        if webhook.get('headers') != '':
            headers.update(ast.literal_eval(webhook['headers']))
        return headers

    def _get_webhook_filters(self, webhook):
        filters = webhook.get('regex_filter')
        if filters != '':
            filters = ast.literal_eval(filters)
            for k, v in filters.items():
                filters[k] = re.compile(v, re.IGNORECASE)
            return filters
        return None

    def _check_against_filter(self, webhook_filters, event):
        # Check if the event matches the specified filters
        if webhook_filters:
            for field, filter in webhook_filters.items():
                value = event.get(field)
                if value is None:
                    return False
                elif filter.match(value) is None:
                    return False
        return True

    def _filter_fields(self, data):
        data = {k: v for k, v in data.items() if k in ALARM_FILTER}
        if data.get(VProps.RESOURCE):
            data[VProps.RESOURCE] = \
                {k: v for k, v in data[VProps.RESOURCE].items() if k in
                 RESOURCE_FILTER}
        return data

    def _check_correct_tenant(self, webhook, data):
        # Check that the resource project ID matches the project ID under
        # which the webhook was added.

        if webhook.get(IS_ADMIN_WEBHOOK):
            return True
        if data.get(VProps.RESOURCE):
            if data[VProps.RESOURCE].get(VProps.PROJECT_ID):
                return data[VProps.RESOURCE][VProps.PROJECT_ID] == \
                    webhook.get(VProps.PROJECT_ID)
        return True
