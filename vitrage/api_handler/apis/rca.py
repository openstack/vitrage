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

from oslo_log import log
from osprofiler import profiler

from vitrage.api_handler.apis import base
from vitrage.common.constants import HistoryProps as HProps
from vitrage.common.constants import TenantProps
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.alarm_properties import AlarmProperties as AProps
from vitrage.graph.driver.networkx_graph import NXGraph
from vitrage.graph import Edge
from vitrage.graph import Vertex
from vitrage.storage import db_time

LOG = log.getLogger(__name__)


@profiler.trace_cls("rca apis",
                    info={}, hide_args=False, trace_private=False)
class RcaApis(base.EntityGraphApisBase):

    @base.lock_graph
    def get_rca(self, ctx, root, all_tenants):
        LOG.debug("RcaApis get_rca - root: %s, all_tenants=%s",
                  root, all_tenants)

        project_id = ctx.get(TenantProps.PROJECT_ID, None)
        is_admin_project = ctx.get(TenantProps.IS_ADMIN, False)

        if all_tenants:
            db_nodes, db_edges = self.db.history_facade.alarm_rca(root)
        else:
            db_nodes, db_edges = self.db.history_facade.alarm_rca(
                root,
                project_id=project_id,
                admin=is_admin_project)

        for n in db_nodes:
            start_timestamp = \
                self.db.history_facade.add_utc_timezone(n.start_timestamp)
            n.payload[HProps.START_TIMESTAMP] = str(start_timestamp)
            if n.end_timestamp <= db_time():
                end_timestamp = \
                    self.db.history_facade.add_utc_timezone(n.end_timestamp)
                n.payload[HProps.END_TIMESTAMP] = str(end_timestamp)
                # TODO(annarez): implement state change in processor and DB
                n.payload[VProps.STATE] = AProps.INACTIVE_STATE

        vertices = [Vertex(vertex_id=n.vitrage_id, properties=n.payload) for n
                    in db_nodes]
        edges = [Edge(source_id=e.source_id, target_id=e.target_id,
                      label=e.label, properties=e.payload) for e in db_edges]
        rca_graph = NXGraph(vertices=vertices, edges=edges)

        json_graph = rca_graph.json_output_graph(
            inspected_index=self._find_rca_index(rca_graph, root))

        return json_graph

    @staticmethod
    def _find_rca_index(found_graph, root):
        for root_index, vertex in enumerate(found_graph._g):
            if vertex == root:
                return root_index
        return 0
