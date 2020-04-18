# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from alembic import script
import contextlib
from unittest import mock

from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import test_fixtures
from oslo_db.sqlalchemy import test_migrations
from oslo_log import log as logging
from oslo_utils import excutils
from oslotest import base as test_base

from vitrage.storage.sqlalchemy import migration
from vitrage.storage.sqlalchemy import models


LOG = logging.getLogger(__name__)


@contextlib.contextmanager
def patch_with_engine(engine):
    with mock.patch.object(enginefacade.writer, 'get_engine') as patch_engine:
        patch_engine.return_value = engine
        yield


class WalkWersionsMixin(object):
    def _walk_versions(self, engine=None, alembic_cfg=None):
        with patch_with_engine(engine):

            script_directory = script.ScriptDirectory.from_config(alembic_cfg)

            self.assertIsNone(self.migration_api.version(alembic_cfg))
            versions = [ver for ver in script_directory.walk_revisions()]

            for version in reversed(versions):
                self._migrate_up(engine, alembic_cfg,
                                 version.revision, with_data=True)

    def _migrate_up(self, engine, config, version, with_data=False):
        """migrate up to a new version of the db.

        We allow for data insertion and post checks at every
        migration version with special _pre_upgrade_### and
        _check_### functions in the main test.
        """

        try:
            if with_data:
                data = None
                pre_upgrade = getattr(
                    self, "_pre_upgrade_%s" % version, None)
                if pre_upgrade:
                    data = pre_upgrade(engine)

            self.migration_api.upgrade(version, config=config)
            self.assertEqual(version, self.migration_api.version(config))

            if with_data:
                check = getattr(self, '_check_%s' % version, None)
                if check:
                    check(engine, data)
        except Exception:
            excutils.save_and_reraise_exception(logger=LOG)


class MigrationCheckersMixin(object):
    def setUp(self):
        super(MigrationCheckersMixin, self).setUp()
        self.engine = enginefacade.writer.get_engine()
        self.config = migration._alembic_config()
        self.migration_api = migration

    def test_walk_versions(self):
        self._walk_versions(self.engine, self.config)

    def test_upgrade_and_version(self):
        with patch_with_engine(self.engine):
            self.migration_api.upgrade('head')
            self.assertIsNotNone(self.migration_api.version())


class TestMigrationsMySQL(MigrationCheckersMixin,
                          WalkWersionsMixin,
                          test_fixtures.OpportunisticDBTestMixin,
                          test_base.BaseTestCase):
    FIXTURE = test_fixtures.MySQLOpportunisticFixture


class ModelsMigrationSyncMixin(object):

    def setUp(self):
        super(ModelsMigrationSyncMixin, self).setUp()
        self.engine = enginefacade.writer.get_engine()

    def get_metadata(self):
        return models.Base.metadata

    def get_engine(self):
        return self.engine

    def db_sync(self, engine):
        with patch_with_engine(engine):
            migration.upgrade('head')


class ModelsMigrationsMySQL(ModelsMigrationSyncMixin,
                            test_migrations.ModelsMigrationsSync,
                            test_fixtures.OpportunisticDBTestMixin,
                            test_base.BaseTestCase):
    FIXTURE = test_fixtures.MySQLOpportunisticFixture
