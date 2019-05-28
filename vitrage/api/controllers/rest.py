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
import networkx as nx
from networkx.readwrite import json_graph
import oslo_messaging
import pecan
from pecan import rest

from vitrage.datasources import OPENSTACK_CLUSTER


class RootRestController(rest.RestController):

    @pecan.expose()
    def _route(self, args, request=None):
        """All requests go through here

        We can check the backend status
        """

        if not pecan.request.check_backend:
            return super(RootRestController, self)._route(args, request)

        try:
            client = pecan.request.client.prepare(timeout=5)
            backend_is_alive = client.call(pecan.request.context, 'is_alive')
            if backend_is_alive:
                return super(RootRestController, self)._route(args, request)
            else:
                pecan.abort(503, detail='vitrage-graph is not ready')
        except oslo_messaging.MessagingTimeout:
            pecan.abort(503, detail='vitrage-graph not available')

    @staticmethod
    def as_tree(graph, root=OPENSTACK_CLUSTER, reverse=False):
        if nx.__version__ >= '2.0':
            linked_graph = json_graph.node_link_graph(
                graph, attrs={'name': 'graph_index'})
        else:
            linked_graph = json_graph.node_link_graph(graph)
        if 0 == nx.number_of_nodes(linked_graph):
            return {}
        if reverse:
            linked_graph = linked_graph.reverse()
        if nx.__version__ >= '2.0':
            return json_graph.tree_data(
                linked_graph,
                root=root,
                attrs={'id': 'graph_index', 'children': 'children'})
        else:
            return json_graph.tree_data(linked_graph, root=root)
