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

import sys

from oslo_config import cfg

from vitrage.cli import VITRAGE_TITLE
from vitrage.common import config
from vitrage import storage
from vitrage.storage.sqlalchemy import migration

CONF = cfg.CONF
CLI_OPTS = [
    cfg.StrOpt('revision',
               default='head',
               help='Migration version')
]
REVISION_OPTS = [
    cfg.StrOpt('message',
               help='Text that will be used for migration title'),
    cfg.BoolOpt('autogenerate',
                default=False,
                help='Generates diff based on current database state')
]


def stamp():
    print(VITRAGE_TITLE)
    CONF.register_cli_opts(CLI_OPTS)
    config.parse_config(sys.argv)

    migration.stamp(CONF.revision)


def revision():
    print(VITRAGE_TITLE)
    CONF.register_cli_opts(REVISION_OPTS)
    config.parse_config(sys.argv)
    migration.revision(CONF.message, CONF.autogenerate)


def dbsync():
    print(VITRAGE_TITLE)
    CONF.register_cli_opts(CLI_OPTS)
    config.parse_config(sys.argv)
    migration.upgrade(CONF.revision)


def purge_data():
    print(VITRAGE_TITLE)
    config.parse_config(sys.argv)
    db = storage.get_connection_from_config()
    db.active_actions.delete()
    db.events.delete()
    db.graph_snapshots.delete()
    db.changes.delete()
    db.edges.delete()
    db.alarms.delete()
