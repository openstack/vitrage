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

from vitrage.common.constants import EdgeProperties as EProps
from vitrage.common.constants import VertexProperties as VProps
from vitrage.graph import Edge
from vitrage.graph import Vertex
from vitrage.utils.datetime import utcnow


LOG = log.getLogger(__name__)


def is_newer_vertex(prev_vertex, new_vertex):
    prev_timestamp = prev_vertex.get(VProps.VITRAGE_SAMPLE_TIMESTAMP)
    if not prev_timestamp:
        return True

    new_timestamp = new_vertex.get(VProps.VITRAGE_SAMPLE_TIMESTAMP)
    if not new_timestamp:
        return True

    return prev_timestamp <= new_timestamp


def is_deleted(item):
    return item and \
        (isinstance(item, Vertex) and
         item.get(VProps.VITRAGE_IS_DELETED, False)) or \
        (isinstance(item, Edge) and
         item.get(EProps.VITRAGE_IS_DELETED, False))


def mark_deleted(g, item):
    if isinstance(item, Vertex):
        if item.get(VProps.VITRAGE_IS_DELETED, False):
            return
        item[VProps.VITRAGE_IS_DELETED] = True
        item[VProps.VITRAGE_SAMPLE_TIMESTAMP] = str(utcnow())
        g.update_vertex(item)
    elif isinstance(item, Edge):
        if item.get(EProps.VITRAGE_IS_DELETED, False):
            return
        item[EProps.VITRAGE_IS_DELETED] = True
        item[EProps.UPDATE_TIMESTAMP] = str(utcnow())
        g.update_edge(item)


def delete_placeholder_vertex(g, vertex):
    """Checks if it is a placeholder vertex, and if so deletes it """

    LOG.debug('Asked to delete a placeholder vertex: %s with %d neighbors',
              vertex, len(g.get_edges(vertex.vertex_id)))

    if not vertex[VProps.VITRAGE_IS_PLACEHOLDER]:
        return
    if not any(True for neighbor_edge in g.get_edges(vertex.vertex_id)
               if not is_deleted(neighbor_edge)):
        LOG.debug("Delete placeholder vertex: %s", vertex)
        g.remove_vertex(vertex)


def find_neighbor_types(neighbors):
    """Finds all the types (TYPE, SUB_TYPE) of the neighbors """

    neighbor_types = set()
    for (vertex, edge) in neighbors:
        neighbor_types.add(get_vertex_types(vertex))
    return neighbor_types


def get_vertex_types(vertex):
    vitrage_category = vertex.get(VProps.VITRAGE_CATEGORY)
    vitrage_type = vertex.get(VProps.VITRAGE_TYPE)
    if not vitrage_category:
        LOG.warning('no vitrage_category in vertex: %s', vertex)
    return vitrage_category, vitrage_type


def update_entity_graph_vertex(g, graph_vertex, updated_vertex):
    if updated_vertex[VProps.VITRAGE_IS_PLACEHOLDER] and \
            graph_vertex and not graph_vertex[VProps.VITRAGE_IS_PLACEHOLDER]:

        updated_vertex[VProps.VITRAGE_IS_PLACEHOLDER] = False
        updated_vertex[VProps.VITRAGE_IS_DELETED] = \
            graph_vertex[VProps.VITRAGE_IS_DELETED]

    g.update_vertex(updated_vertex,
                    not updated_vertex[VProps.VITRAGE_IS_PLACEHOLDER])
