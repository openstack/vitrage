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

import json
from oslo_log import log
from osprofiler import profiler

from vitrage.common.constants import TemplateStatus as TStatus
from vitrage.evaluator.template_db import template_repository as template_repo
from vitrage.evaluator.template_schema_factory import TemplateSchemaFactory


LOG = log.getLogger(__name__)


@profiler.trace_cls("template apis",
                    info={}, hide_args=False, trace_private=False)
class TemplateApis(object):

    FAILED_MSG = 'validation failed'
    OK_MSG = 'validation OK'

    def __init__(self, notifier=None, db=None):
        self.notifier = notifier
        self.db = db

    def validate_template(self, ctx, templates, template_type, params=None):
        LOG.debug("TemplateApis validate_template type: %s content: %s",
                  template_type, templates)

        files_content = [t[1] for t in templates]
        paths = [t[0] for t in templates]
        results = template_repo.validate_templates(self.db, files_content,
                                                   template_type, params)
        results = [_to_result(r, p) for r, p in zip(results, paths)]
        return json.dumps({'results': results})

    def template_versions(self, ctx):
        versions = sorted(TemplateSchemaFactory.supported_versions())
        # TODO(eyalb) at the moment all are supported
        current = max(versions)
        return [
            {
                'version': 'v%s' % version,
                'status': 'SUPPORTED' if version < current else 'CURRENT'
            }
            for version in versions
        ]

    def add_template(self, ctx, templates, template_type, params=None):
        """Signal the evaluator

         A new template has been added to the database with a status of
         LOADING that needs to be handled.
        """
        LOG.debug("TemplateApis add_template type: %s content: %s params: %s",
                  template_type, templates, params)

        files_content = [t[1] for t in templates]
        db_rows = template_repo.add_templates_to_db(self.db, files_content,
                                                    template_type, params)
        if self._is_evaluator_reload_required(db_rows):
            LOG.info("Adding templates..")
            self.notifier.notify("add template", {'template_action': 'add'})

        return [_db_template_to_dict(r) for r in db_rows]

    def _is_evaluator_reload_required(self, db_rows):
        """Is  evaluator reload required

        If all the templates have error status, no need to reload evaluators
        """
        return any([True for t in db_rows if t.status != TStatus.ERROR])

    def delete_template(self, ctx, uuids):
        """Signal the evaluator

         A template status has been changed to DELETING.
        """
        db = self.db

        if type(uuids) != list:
            uuids = [uuids]
        LOG.info("Deleting templates %s ", uuids)
        templates = [t for _id in uuids for t in db.templates.query(uuid=_id)
                     if t.status != TStatus.DELETED]
        if not templates:
            return
        for t in templates:
            if t.status == TStatus.ERROR:
                db.templates.update(t.uuid, "status", TStatus.DELETED)
            else:
                db.templates.update(t.uuid, "status", TStatus.DELETING)
        if self._is_evaluator_reload_required(templates):
            self.notifier.notify("delete template",
                                 {'template_action': 'delete'})


def _to_result(result, template_path):
    if result.is_valid_config:
        return {
            'file path': template_path,
            'status': TemplateApis.OK_MSG,
            'description': 'Template validation',
            'message': str(result.comment),
            'status code': result.status_code
        }
    else:
        return {
            'file path': template_path,
            'status': TemplateApis.FAILED_MSG,
            'description': result.description,
            'message': str(result.comment),
            'status code': result.status_code
        }


def _db_template_to_dict(template):
    return {
        "uuid": template.uuid,
        "name": template.name,
        "status": template.status,
        "date": str(template.created_at),
        "status details": template.status_details,
        "type": template.template_type,
    }
