# Copyright 2017 - Nokia
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
import os
import sys
import yaml

from vitrage.common.constants import TemplateStatus
from vitrage.common.constants import TemplateTypes as TType
from vitrage.evaluator.template_db.template_repository import \
    add_templates_to_db
from vitrage import storage
from vitrage.storage.sqlalchemy import models


class TestConfiguration(object):

    def add_db(self):
        db_name = "sqlite:///test-%s-%s.db" % (type(self).__name__,
                                               sys.version_info[0])
        self.config(group='database', connection=db_name)
        self._db = storage.get_connection_from_config()
        engine = self._db._engine_facade.get_engine()
        models.Base.metadata.drop_all(engine)
        models.Base.metadata.create_all(engine)
        return self._db

    def add_templates(self, templates_dir, templates_type=TType.STANDARD):
        yamls = [t for t in TestConfiguration.load_yaml_files(templates_dir)]
        templates = add_templates_to_db(self._db, yamls, templates_type)
        for t in templates:
            if t.status == TemplateStatus.LOADING:
                self._db.templates.update(t.uuid, 'status',
                                          TemplateStatus.ACTIVE)
            if t.status == TemplateStatus.DELETING:
                self._db.templates.update(t.uuid, 'status',
                                          TemplateStatus.DELETED)
        return templates

    @staticmethod
    def load_yaml_files(path):
        if os.path.isdir(path):
            file_paths = [path + "/" + fn for fn in os.listdir(path)
                          if os.path.isfile(path + "/" + fn)]
        else:
            file_paths = [path]

        yamls = []
        for file_path in file_paths:
            try:
                yamls.append(TestConfiguration._load_yaml_file(file_path))
            except Exception:
                continue
        return yamls

    @staticmethod
    def _load_yaml_file(path):
        with open(path, 'r') as stream:
            return yaml.load(stream, Loader=yaml.BaseLoader)
