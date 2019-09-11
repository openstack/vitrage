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
import datetime
import json
import zlib

from oslo_db.sqlalchemy import models

from sqlalchemy import Column, DateTime, INTEGER, String, \
    SmallInteger, BigInteger, Index, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import sqlalchemy.types as types


DEFAULT_END_TIME = datetime.datetime(2222, 2, 22, 22, 22, 22)


class VitrageBase(models.TimestampMixin, models.ModelBase):
    """Base class for Vitrage Models."""
    __table_args__ = {'mysql_charset': "utf8",
                      'mysql_engine': "InnoDB"}
    __table_initialized__ = False

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def update(self, values):
        """Make the model object behave like a dict."""
        for k, v in values.items():
            setattr(self, k, v)


Base = declarative_base(cls=VitrageBase)


class AutoIncrementInteger(types.TypeDecorator):
    impl = types.INT
    count = 0

    def process_bind_param(self, value, dialect):
        value = self.count
        self.count += 1
        return value

    def process_result_value(self, value, dialect):
        return value


MagicBigInt = types.BigInteger().with_variant(AutoIncrementInteger, 'sqlite')


class JSONEncodedDict(types.TypeDecorator):
    """Represents an immutable structure as a json-encoded string"""

    impl = types.TEXT

    def process_bind_param(self, value, dialect):
        return json.dumps(value) if value else None

    def process_result_value(self, value, dialect):
        return json.loads(value) if value else None


class CompressedBinary(types.TypeDecorator):
    impl = types.LargeBinary

    def process_bind_param(self, value, dialect):
        return zlib.compress(value) if value else None

    def process_result_value(self, value, dialect):
        return zlib.decompress(value) if value else None

    def copy(self, **kwargs):
        return CompressedBinary(self.impl.length)


class Event(Base):

    __tablename__ = 'events'

    event_id = Column("id", BigInteger(), primary_key=True, autoincrement=True)
    payload = Column(JSONEncodedDict(), nullable=False)
    is_vertex = Column(Boolean, nullable=False)

    def __repr__(self):
        return \
            "<Event(" \
            "id='%s', " \
            "is_vertex='%s', " \
            "payload='%s')>" % \
            (
                self.event_id,
                self.is_vertex,
                self.payload
            )


class ActiveAction(Base):
    __tablename__ = 'active_actions'
    __table_args__ = (
        # Index 'ix_active_action' on fields:
        # action_type, extra_info, source_vertex_id, target_vertex_id
        Index('ix_active_action', 'action_type', 'extra_info',
              'source_vertex_id', 'target_vertex_id'),
    )

    action_type = Column(String(128))
    extra_info = Column(String(128))
    source_vertex_id = Column(String(128))
    target_vertex_id = Column(String(128))
    action_id = Column(String(128), primary_key=True)
    score = Column(SmallInteger())
    trigger = Column(String(128), primary_key=True)

    def __repr__(self):
        return \
            "<ActiveAction(" \
            "created_at='%s', " \
            "action_type='%s', " \
            "extra_info='%s', " \
            "source_vertex_id='%s', " \
            "target_vertex_id='%s', " \
            "action_id='%s', " \
            "score='%s', " \
            "trigger='%s')>" % \
            (
                self.created_at,
                self.action_type,
                self.extra_info,
                self.source_vertex_id,
                self.target_vertex_id,
                self.action_id,
                self.score,
                self.trigger
            )


class GraphSnapshot(Base):
    __tablename__ = 'graph_snapshots'

    snapshot_id = Column("id", INTEGER, primary_key=True)
    event_id = Column(BigInteger, nullable=False)
    graph_snapshot = Column(CompressedBinary((2 ** 32) - 1), nullable=False)

    def __repr__(self):
        return \
            "<GraphSnapshot(" \
            "id=%s," \
            "event_id='%s', " \
            "graph_snapshot='%s')>" %\
            (
                self.snapshot_id,
                self.event_id,
                self.graph_snapshot
            )


class Template(Base):
    __tablename__ = 'templates'

    uuid = Column("id", String(64), primary_key=True, nullable=False)
    status = Column(String(16))
    status_details = Column(String(128))
    name = Column(String(128), nullable=False)
    file_content = Column(JSONEncodedDict, nullable=False)
    template_type = Column("type", String(64), default='standard')

    def __repr__(self):
        return "<Template(id='%s', name='%s', created_at='%s'," \
               " updated_at='%s', status='%s'," \
               "status_details='%s', file_content='%s', " \
               " template_type='%s' )>" % \
               (self.uuid,
                self.name,
                self.created_at,
                self.updated_at,
                self.status,
                self.status_details,
                self.file_content,
                self.template_type,)


class Webhooks(Base):
    __tablename__ = 'webhooks'

    id = Column(String(128), primary_key=True)
    project_id = Column(String(128), nullable=False)
    is_admin_webhook = Column(Boolean, nullable=False)
    url = Column(String(256), nullable=False)
    headers = Column(String(1024))
    regex_filter = Column(String(512))

    def __repr__(self):
        return \
            "<Webhook(" \
            "id='%s', " \
            "created_at='%s', " \
            "updated_at='%s', " \
            "project_id='%s', " \
            "is_admin_webhook='%s', " \
            "url='%s', " \
            "headers='%s', " \
            "regex_filter='%s')> " %\
            (
                self.id,
                self.created_at,
                self.updated_at,
                self.project_id,
                self.is_admin_webhook,
                self.url,
                self.headers,
                self.regex_filter
            )


class Alarm(Base):

    __tablename__ = 'alarms'

    vitrage_id = Column(String(128), primary_key=True)
    start_timestamp = Column(DateTime, index=True, nullable=False)
    end_timestamp = Column(DateTime, index=True, nullable=False,
                           default=DEFAULT_END_TIME)
    name = Column(String(256), nullable=False)
    vitrage_type = Column(String(64), nullable=False)
    vitrage_aggregated_severity = Column(String(64), index=True,
                                         nullable=False)
    vitrage_operational_severity = Column(String(64), index=True,
                                          nullable=False)
    project_id = Column(String(64), index=True)
    vitrage_resource_type = Column(String(64))
    vitrage_resource_id = Column(String(64))
    vitrage_resource_project_id = Column(String(64), index=True)
    payload = Column(JSONEncodedDict())

    def __repr__(self):
        return \
            "<Alarm(" \
            "vitrage_id='%s', " \
            "start_timestamp='%s', " \
            "end_timestamp='%s'," \
            "name='%s'," \
            "vitrage_type='%s'," \
            "vitrage_aggregated_severity='%s'," \
            "vitrage_operational_severity='%s'," \
            "project_id='%s'," \
            "vitrage_resource_type='%s'," \
            "vitrage_resource_id='%s'," \
            "vitrage_resource_project_id='%s'," \
            "payload='%s')>" % \
            (
                self.vitrage_id,
                self.start_timestamp,
                self.end_timestamp,
                self.name,
                self.vitrage_type,
                self.vitrage_aggregated_severity,
                self.vitrage_operational_severity,
                self.project_id,
                self.vitrage_resource_type,
                self.vitrage_resource_id,
                self.vitrage_resource_project_id,
                self.payload
            )


class Edge(Base):

    __tablename__ = 'edges'

    source_id = Column(String(128),
                       ForeignKey('alarms.vitrage_id', ondelete='CASCADE'),
                       primary_key=True)
    target_id = Column(String(128),
                       ForeignKey('alarms.vitrage_id', ondelete='CASCADE'),
                       primary_key=True)
    label = Column(String(64), nullable=False)
    start_timestamp = Column(DateTime, nullable=False)
    end_timestamp = Column(DateTime, nullable=False, default=DEFAULT_END_TIME)
    payload = Column(JSONEncodedDict())

    source = relationship("Alarm", foreign_keys=[source_id])
    target = relationship("Alarm", foreign_keys=[target_id])

    def __repr__(self):
        return \
            "<Edge(" \
            "source_id='%s', " \
            "target_id='%s', " \
            "label='%s', " \
            "start_timestamp='%s'," \
            "end_timestamp='%s',"\
            "payload='%s)>" % \
            (
                self.source_id,
                self.target_id,
                self.label,
                self.start_timestamp,
                self.end_timestamp,
                self.payload
            )


class Change(Base):

    __tablename__ = 'changes'

    id = Column(MagicBigInt, primary_key=True, autoincrement=True)
    vitrage_id = Column(String(128),
                        ForeignKey('alarms.vitrage_id', ondelete='CASCADE'),
                        index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    severity = Column(String(64), index=True, nullable=False)
    payload = Column(JSONEncodedDict())

    alarm_id = relationship("Alarm", foreign_keys=[vitrage_id])

    def __repr__(self):
        return \
            "<Change(" \
            "id='%s', " \
            "vitrage_id='%s', " \
            "timestamp='%s', " \
            "severity='%s'," \
            "payload='%s')>" % \
            (
                self.id,
                self.vitrage_id,
                self.timestamp,
                self.severity,
                self.payload
            )
