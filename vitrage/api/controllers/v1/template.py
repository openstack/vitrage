# Copyright 2016 - Nokia Corporation
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

from datetime import timedelta
import json
import time

import pecan
from pytz import utc

from oslo_log import log
from oslo_utils.uuidutils import is_uuid_like
from osprofiler import profiler
from pecan.core import abort

from vitrage.api.controllers.rest import RootRestController
from vitrage.api.policy import enforce
from vitrage.common.constants import TemplateStatus as TStatus
from vitrage.common.exception import VitrageError

LOG = log.getLogger(__name__)

ONE_HOUR = int(timedelta(hours=1).total_seconds())


class TemplateVersionsController(RootRestController):
    @pecan.expose('json')
    def index(self):
        return self.get()

    @pecan.expose('json')
    def get(self):
        LOG.info('get template versions')

        try:
            return pecan.request.client.call(pecan.request.context,
                                             'template_versions')
        except Exception:
            LOG.exception('Failed to get template versions')
            abort(404, 'Failed to get template versions')


@profiler.trace_cls("template controller",
                    info={}, hide_args=False, trace_private=False)
class TemplateController(RootRestController):

    versions = TemplateVersionsController()

    @pecan.expose('json')
    def get_all(self):

        LOG.info('returns template list')

        enforce("template list",
                pecan.request.headers,
                pecan.request.enforcer,
                {})
        try:
            return self._get_templates()
        except Exception:
            LOG.exception('failed to get template list.')
            abort(404, 'Failed to get template list')

    @pecan.expose('json')
    def get(self, _id):

        LOG.info('get template content')

        enforce("template show",
                pecan.request.headers,
                pecan.request.enforcer,
                {})

        try:
            return self._show_template(_id)
        except Exception:
            LOG.exception('Failed to show template %s.', _id)
            abort(404, 'Failed to show template.')

    @pecan.expose('json')
    def delete(self, **kwargs):
        # for backward computability
        values = kwargs['uuid'] if 'uuid'in kwargs else kwargs['id']
        LOG.info("delete template. values: %s", values)
        uuids = self._to_uuids(values)
        LOG.info("delete template. uuids: %s", uuids)

        enforce("template delete",
                pecan.request.headers,
                pecan.request.enforcer,
                {})
        try:
            return self._delete(uuids)
        except Exception:
            LOG.exception('Failed to delete template.')
            abort(404, 'Failed to delete template.')

    @pecan.expose('json')
    def put(self, **kwargs):
        templates = kwargs['templates']
        LOG.info("add template: %s", templates)

        enforce("template add",
                pecan.request.headers,
                pecan.request.enforcer,
                {})
        template_type = kwargs['template_type']
        params = kwargs.get('params')
        overwrite = kwargs.get('overwrite')

        if overwrite:
            names = [
                template[1]['metadata']['name']
                for template in templates
            ]

            uuids = self._to_uuids(names)
            self._delete_templates_and_wait(uuids)

        try:
            return self._add(templates, template_type, params)
        except Exception:
            LOG.exception('Failed to add template.')
            abort(404, 'Failed to add template.')

    @pecan.expose('json')
    def post(self, **kwargs):

        LOG.info('validate template. args: %s', kwargs)

        enforce("template validate",
                pecan.request.headers,
                pecan.request.enforcer,
                {})

        templates = kwargs['templates']
        template_type = kwargs.get('template_type')
        params = kwargs.get('params')

        try:
            return self._validate(templates, template_type, params)
        except Exception:
            LOG.exception('Failed to validate template(s).')
            abort(404, 'Failed to validate template(s).')

    @classmethod
    def _get_templates(cls):
        try:
            templates = pecan.request.storage.templates.query()
            for template in templates:
                template.created_at = utc.localize(template.created_at)
                if template.updated_at:
                    template.updated_at = utc.localize(template.updated_at)
            templates = [t for t in templates if t.status != TStatus.DELETED]
            templates.sort(key=lambda templ: templ.created_at)
            return [cls._db_template_to_dict(t) for t in templates]
        except Exception:
            LOG.exception('Failed to get template list.')
            abort(404, 'Failed to get template list.')

    @staticmethod
    def _show_template(_id):
        uuid = TemplateController._to_uuid(_id)
        try:
            templates = pecan.request.storage.templates.query(uuid=uuid)
            if not templates or templates[0].status == TStatus.DELETED:
                raise VitrageError("Template %s not found", uuid)
            return templates[0].file_content
        except Exception:
            LOG.exception('Failed to show template with uuid: %s ', uuid)
            abort(404, 'Failed to show template.')

    @staticmethod
    def _validate(templates, template_type, params):

        result_json = pecan.request.client.call(pecan.request.context,
                                                'validate_template',
                                                templates=templates,
                                                template_type=template_type,
                                                params=params)
        try:
            return json.loads(result_json)
        except Exception:
            LOG.exception('Failed to open template file(s).')
            abort(404, 'Failed to validate template file.')

    @classmethod
    def _add(cls, templates, template_type, params):
        try:
            results = pecan.request.client.call(
                pecan.request.context,
                'add_template',
                templates=templates,
                template_type=template_type,
                params=params,
            )
            return results
        except Exception:
            LOG.exception('Failed to add template file.')
            abort(404, 'Failed to add template file.')

    @staticmethod
    def _db_template_to_dict(template):
        return {
            "uuid": template.uuid,
            "name": template.name,
            "status": template.status,
            "date": template.created_at,
            "status details": template.status_details,
            "type": template.template_type,
        }

    @staticmethod
    def _delete(uuids):
        try:
            results = pecan.request.client.call(
                pecan.request.context,
                'delete_template',
                uuids=uuids)
            return results
        except Exception:
            LOG.exception('Failed to delete template.')
            abort(404, 'Failed to delete template.')

    def _to_uuids(self, values):
        # if it is a single string
        # make sure I don't iterate
        # on the characters
        if type(values) is not list:
            values = [values]

        return [self._to_uuid(val) for val in values]

    @staticmethod
    def _to_uuid(val):
        if is_uuid(val):
            return val
        template = pecan.request.storage.templates.query_with_status_not(
            status=TStatus.DELETED, name=val)
        if template:
            return template.uuid
        return val

    def _delete_templates_and_wait(self, uuids):
        self._delete(uuids)

        def check_deleted():
            for _id in uuids:
                try:
                    self._show_template(_id)
                except Exception:  # if deleted we get exception
                    pass
                else:
                    return False
            return True

        return wait_for_action_to_end(ONE_HOUR, check_deleted)


def is_uuid(val):
    # unwrap the name or id
    # from the list if in a list
    # [value] --> value
    if type(val) is list:
        val, = val
    return is_uuid_like(val)


def wait_for_action_to_end(timeout, func, **kwargs):
    count = 0
    while count < timeout:
        if func(**kwargs):
            return True
        count += 1
        time.sleep(1)
    return False
