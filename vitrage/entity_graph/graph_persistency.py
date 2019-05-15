# Copyright 2018 - Nokia
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
from oslo_log import log

from vitrage.common.constants import VertexProperties as VProps
from vitrage.graph import Edge
from vitrage.graph import Vertex

from vitrage.storage.sqlalchemy import models


LOG = log.getLogger(__name__)


class GraphPersistency(object):
    def __init__(self, db, graph):
        self.db = db
        self.graph = graph
        self.events_buffer = []

    def store_graph(self):
        LOG.info('Persisting graph...')
        try:
            last_event_id = self.db.events.get_last_event_id()
            last_event_id = last_event_id.event_id if last_event_id else 0
            graph_snapshot = self.graph.write_gpickle()
            self.db.graph_snapshots.update(models.GraphSnapshot(
                snapshot_id=1,
                event_id=last_event_id,
                graph_snapshot=graph_snapshot))
            LOG.info('Persisting graph - done')
        except Exception:
            LOG.exception("Graph is not stored")

    def query_recent_snapshot(self):
        return self.db.graph_snapshots.query()

    def replay_events(self, graph, event_id):
        LOG.info('Getting events from database')
        count = self.do_replay_events(self.db, graph, event_id)
        LOG.info('%s database events applied ', count)

    @staticmethod
    def do_replay_events(db, graph, event_id):
        events = db.events.get_replay_events(
            event_id=event_id)

        for event in events:
            if event.is_vertex:
                v_id = event.payload['vertex_id']
                del event.payload['vertex_id']
                v = Vertex(v_id, event.payload)
                graph.update_vertex(v)
            else:
                source_id = event.payload['source_id']
                target_id = event.payload['target_id']
                label = event.payload['label']
                del event.payload['source_id']
                del event.payload['target_id']
                del event.payload['label']
                e = Edge(source_id, target_id, label, event.payload)
                graph.update_edge(e)
        return len(events)

    def persist_event(self, before, current, is_vertex, graph, event_id=None):
        """Callback subscribed to driver.graph updates"""
        if not self.is_important_change(
                before, current, VProps.UPDATE_TIMESTAMP,
                VProps.VITRAGE_SAMPLE_TIMESTAMP):
            return

        if is_vertex:
            curr = current.properties.copy()
            curr['vertex_id'] = current.vertex_id
        else:
            curr = current.properties.copy()
            curr['source_id'] = current.source_id
            curr['target_id'] = current.target_id
            curr['label'] = current.label

        event_row = models.Event(payload=curr, is_vertex=is_vertex,
                                 event_id=event_id)
        self.events_buffer.append(event_row)

    def flush_events(self):
        if not self.events_buffer:
            return
        self.db.events.bulk_create(self.events_buffer)
        self.events_buffer = []

    @staticmethod
    def is_important_change(before, curr, *args):
        """Non important changes such as update_timestamp shouldn't be stored

        :param args: list of keys that should be ignored
        :return: True if this change should be stored
        """
        if not curr:
            return False
        if curr and not before:
            return True
        for key, content in curr.properties.items():
            if key in args:
                continue
            elif isinstance(content, dict) or isinstance(content, list):
                return True  # TODO(ihefetz): can be improved
            elif before.properties.get(key) != content:
                return True
        return False
