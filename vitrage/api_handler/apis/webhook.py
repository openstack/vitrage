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
import ast
from collections import namedtuple
import datetime
from oslo_log import log
from oslo_utils import uuidutils
from osprofiler import profiler
import re
from urllib.parse import urlparse
from vitrage.common.constants import TenantProps
from vitrage.common.constants import VertexProperties as Vprops
from vitrage.notifier.plugins.webhook.utils import db_row_to_dict
from vitrage.storage.sqlalchemy.models import Webhooks

LOG = log.getLogger(__name__)

Result = namedtuple("Result", ["is_valid", "message"])


@profiler.trace_cls("webhook apis",
                    info={}, hide_args=False, trace_private=False)
class WebhookApis(object):
    DELETED_ROWS_SUCCESS = 1

    def __init__(self, db):
        self.db_conn = db

    def delete_webhook(self, ctx, id):

        LOG.info("Delete webhook with id: %s", id)

        deleted_rows_count = self.db_conn.webhooks.delete(id)

        if deleted_rows_count == self.DELETED_ROWS_SUCCESS:
            return {'SUCCESS': 'Webhook %s deleted' % id}
        else:
            return None

    def get_all_webhooks(self, ctx, all_tenants):
        LOG.info("List all webhooks")
        if all_tenants and ctx.get(TenantProps.IS_ADMIN, False):
            res = self.db_conn.webhooks.query()
        else:
            res = self.db_conn.webhooks.query(project_id=ctx.get(
                TenantProps.PROJECT_ID, ""))
        LOG.info(res)
        webhooks = [db_row_to_dict(webhook) for webhook in res]

        return webhooks

    def add_webhook(self, ctx, url, headers=None, regex_filter=None):
        res = self._check_valid_webhook(url, headers, regex_filter)
        if not res.is_valid:
            LOG.exception("Failed to create webhook: %s" % res.message)
            return res.message
        try:
            db_row = self._webhook_to_db_row(url, headers, regex_filter, ctx)
            self.db_conn.webhooks.create(db_row)
            return db_row_to_dict(db_row)
        except Exception as e:
            LOG.exception("Failed to add webhook to DB")
            return {"ERROR": str(e)}

    def get_webhook(self, ctx, id):
        try:
            webhooks = self.db_conn.webhooks.query(id=id)
            # Check that webhook belongs to current tenant or current tenant
            #  is admin
            if len(webhooks) == 0:
                LOG.warning("Webhook not found - %s" % id)
                return None
            if ctx.get(TenantProps.PROJECT_ID, "") == \
                    webhooks[0][Vprops.PROJECT_ID] or ctx.get(
                    TenantProps.IS_ADMIN, False):
                return webhooks[0]
            else:
                LOG.warning('Webhook show - Authorization failed (%s)',
                            id)
                return None
        except Exception as e:
            LOG.exception("Failed to get webhook")
            return {"ERROR": str(e)}

    def _webhook_to_db_row(self, url, headers, regex_filter, ctx):
        if not regex_filter:
            regex_filter = ""
        if not headers:
            headers = ""
        uuid = uuidutils.generate_uuid()
        project_id = ctx.get(TenantProps.PROJECT_ID, "")
        is_admin = ctx.get(TenantProps.IS_ADMIN, False)
        created_at = str(datetime.datetime.now())
        db_row = Webhooks(id=uuid,
                          project_id=project_id,
                          is_admin_webhook=is_admin,
                          created_at=created_at,
                          url=url,
                          headers=headers,
                          regex_filter=regex_filter)
        return db_row

    def _check_valid_webhook(self, url, headers, regex_filter):
        if not self._validate_url(url):
            return Result(False, {"ERROR": "Invalid URL"})
        elif not self._validate_headers(headers):
            return Result(False, {"ERROR": "Headers in invalid format"})
        elif not self._validate_regex(regex_filter):
            return Result(False, {"ERROR": "Invalid RegEx"})
        return Result(True, "")

    def _validate_url(self, url):
        try:
            result = urlparse(url)
            if not result.scheme or not result.netloc:
                return False
        except Exception:
            return False
        return True

    def _validate_regex(self, regex_filter):
        if regex_filter:
            try:
                filter_dict = ast.literal_eval(regex_filter)
                if not isinstance(filter_dict, dict):
                    return False
                for filter in filter_dict.values():
                    re.compile(filter)
            except Exception:
                return False
        return True

    def _validate_headers(self, headers):
        if headers:
            try:
                return isinstance(ast.literal_eval(headers), dict)
            except Exception:
                return False
        return True
