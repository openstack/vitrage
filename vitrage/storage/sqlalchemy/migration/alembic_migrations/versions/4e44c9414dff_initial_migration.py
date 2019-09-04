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

from alembic import op
from oslo_utils import timeutils
import sqlalchemy as sa

from vitrage.storage.sqlalchemy import models


"""Initial migration"

Revision ID: 4e44c9414dff
Revises: None
Create Date: 2019-09-04 15:35:01.086784

"""

# revision identifiers, used by Alembic.
revision = '4e44c9414dff'
down_revision = None


def upgrade():
    try:
        op.create_table(
            'alarms',
            sa.Column('vitrage_id', sa.String(128), primary_key=True),
            sa.Column('start_timestamp', sa.DateTime, nullable=False),
            sa.Column('end_timestamp', sa.DateTime, nullable=False,
                      default=models.DEFAULT_END_TIME),
            sa.Column('name', sa.String(256), nullable=False),
            sa.Column('vitrage_type', sa.String(64), nullable=False),
            sa.Column('vitrage_aggregated_severity', sa.String(64),
                      nullable=False),
            sa.Column('vitrage_operational_severity', sa.String(64),
                      nullable=False),
            sa.Column('project_id', sa.String(64)),
            sa.Column('vitrage_resource_type', sa.String(64)),
            sa.Column('vitrage_resource_id', sa.String(64)),
            sa.Column('vitrage_resource_project_id', sa.String(64)),
            sa.Column('payload', models.JSONEncodedDict),

            sa.Column('created_at', sa.DateTime,
                      default=lambda: timeutils.utcnow()),
            sa.Column('updated_at', sa.DateTime,
                      onupdate=lambda: timeutils.utcnow()),
            mysql_charset='utf8',
            mysql_engine='InnoDB'
        )

        op.create_table(
            'edges',
            sa.Column('source_id', sa.String(128), primary_key=True),
            sa.Column('target_id', sa.String(128), primary_key=True),
            sa.Column('label', sa.String(64), nullable=False),
            sa.Column('start_timestamp', sa.DateTime, nullable=False),
            sa.Column('end_timestamp', sa.DateTime, nullable=False,
                      default=models.DEFAULT_END_TIME),
            sa.Column('payload', models.JSONEncodedDict),

            sa.Column('created_at', sa.DateTime,
                      default=lambda: timeutils.utcnow()),
            sa.Column('updated_at', sa.DateTime,
                      onupdate=lambda: timeutils.utcnow()),
            sa.ForeignKeyConstraint(['source_id'], ['alarms.vitrage_id'],
                                    ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['target_id'], ['alarms.vitrage_id'],
                                    ondelete='CASCADE'),
            mysql_charset='utf8',
            mysql_engine='InnoDB'
        )

        op.create_table(
            'changes',
            sa.Column('id', models.MagicBigInt, primary_key=True,
                      autoincrement=True),
            sa.Column('vitrage_id', sa.String(128), nullable=False),
            sa.Column('timestamp', sa.DateTime, nullable=False),
            sa.Column('severity', sa.String(64), nullable=False),
            sa.Column('payload', models.JSONEncodedDict),

            sa.Column('created_at', sa.DateTime,
                      default=lambda: timeutils.utcnow()),
            sa.Column('updated_at', sa.DateTime,
                      onupdate=lambda: timeutils.utcnow()),
            sa.ForeignKeyConstraint(['vitrage_id'], ['alarms.vitrage_id'],
                                    ondelete='CASCADE'),
            mysql_charset='utf8',
            mysql_engine='InnoDB'
        )

        op.create_table(
            'active_actions',
            sa.Column('action_type', sa.String(128)),
            sa.Column('extra_info', sa.String(128)),
            sa.Column('source_vertex_id', sa.String(128)),
            sa.Column('target_vertex_id', sa.String(128)),
            sa.Column('action_id', sa.String(128), primary_key=True),
            sa.Column('score', sa.SmallInteger()),
            sa.Column('trigger', sa.String(128), primary_key=True),
            sa.Column('created_at', sa.DateTime,
                      default=lambda: timeutils.utcnow()),
            sa.Column('updated_at', sa.DateTime,
                      onupdate=lambda: timeutils.utcnow()),
            mysql_charset='utf8',
            mysql_engine='InnoDB'
        )
        op.create_table(
            'templates',
            sa.Column('id', sa.String(64), primary_key=True, nullable=False),
            sa.Column('status', sa.String(16)),
            sa.Column('status_details', sa.String(128)),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('file_content', models.JSONEncodedDict, nullable=False),
            sa.Column("type", sa.String(64), default='standard'),
            sa.Column('created_at', sa.DateTime,
                      default=lambda: timeutils.utcnow()),
            sa.Column('updated_at', sa.DateTime,
                      onupdate=lambda: timeutils.utcnow()),
            mysql_charset='utf8',
            mysql_engine='InnoDB'
        )
        op.create_table(
            'webhooks',
            sa.Column('id', sa.String(128), primary_key=True),
            sa.Column('project_id', sa.String(128), nullable=False),
            sa.Column('is_admin_webhook', sa.Boolean, nullable=False),
            sa.Column('url', sa.String(256), nullable=False),
            sa.Column('headers', sa.String(1024)),
            sa.Column('regex_filter', sa.String(512)),
            sa.Column('created_at', sa.DateTime,
                      default=lambda: timeutils.utcnow()),
            sa.Column('updated_at', sa.DateTime,
                      onupdate=lambda: timeutils.utcnow()),
            mysql_charset='utf8',
            mysql_engine='InnoDB'
        )
        op.create_index(
            'ix_active_action',
            'active_actions',
            [
                'action_type', 'extra_info', 'source_vertex_id',
                'target_vertex_id'
            ]
        )

        op.create_table(
            'events',
            sa.Column("id", sa.BigInteger, primary_key=True, nullable=False,
                      autoincrement=True),
            sa.Column('payload', models.JSONEncodedDict(), nullable=False),
            sa.Column('is_vertex', sa.Boolean, nullable=False),
            sa.Column('created_at', sa.DateTime,
                      default=lambda: timeutils.utcnow()),
            sa.Column('updated_at', sa.DateTime,
                      onupdate=lambda: timeutils.utcnow()),
            mysql_charset='utf8',
            mysql_engine='InnoDB'
        )
        op.create_table(
            'graph_snapshots',
            sa.Column('id', sa.Integer, primary_key=True,
                      nullable=False),
            sa.Column('event_id', sa.BigInteger, nullable=False),
            sa.Column('graph_snapshot', models.CompressedBinary((2 ** 32) - 1),
                      nullable=False),
            sa.Column('created_at', sa.DateTime,
                      default=lambda: timeutils.utcnow()),
            sa.Column('updated_at', sa.DateTime,
                      onupdate=lambda: timeutils.utcnow()),
            mysql_charset='utf8',
            mysql_engine='InnoDB'
        )

        op.create_index(
            'ix_alarms_end_timestamp',
            'alarms',
            [
                'end_timestamp'
            ]
        )

        op.create_index(
            'ix_alarms_project_id',
            'alarms',
            [
                'project_id'
            ]
        )

        op.create_index(
            'ix_alarms_start_timestamp',
            'alarms',
            [
                'start_timestamp'
            ]
        )

        op.create_index(
            'ix_alarms_vitrage_aggregated_severity',
            'alarms',
            [
                'vitrage_aggregated_severity'
            ]
        )

        op.create_index(
            'ix_alarms_vitrage_operational_severity',
            'alarms',
            [
                'vitrage_operational_severity'
            ]
        )

        op.create_index(
            'ix_alarms_vitrage_resource_project_id',
            'alarms',
            [
                'vitrage_resource_project_id'
            ]
        )

        op.create_index(
            'ix_changes_severity',
            'changes',
            [
                'severity'
            ]
        )
        op.create_index(
            'ix_changes_timestamp',
            'changes',
            [
                'timestamp'
            ]
        )

        op.create_index(
            'ix_changes_vitrage_id',
            'changes',
            [
                'vitrage_id'
            ]
        )
    except Exception:
        # TODO(e0ne): figure out more specific exception here to handle a case
        # when migration is applied over Queens release and tables are already
        # exists
        pass
