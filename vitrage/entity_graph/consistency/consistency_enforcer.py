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

from datetime import timedelta

from oslo_log import log

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EntityCategory
from vitrage.common.constants import GraphAction
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.consistency import CONSISTENCY_DATASOURCE
from vitrage.datasources import OPENSTACK_CLUSTER
from vitrage.datasources import utils
from vitrage.entity_graph import EVALUATOR_TOPIC
from vitrage.evaluator.actions.evaluator_event_transformer \
    import VITRAGE_DATASOURCE
from vitrage.messaging import VitrageNotifier
from vitrage.utils.datetime import utcnow

LOG = log.getLogger(__name__)


class ConsistencyEnforcer(object):

    def __init__(self,
                 conf,
                 entity_graph,
                 actions_callback=None):
        self.conf = conf
        self.actions_callback = actions_callback or VitrageNotifier(
            conf, 'vitrage_consistency', [EVALUATOR_TOPIC]).notify
        self.graph = entity_graph
        self._init_datasources_to_mark_deleted()

    # noinspection PyBroadException
    def periodic_process(self):
        try:
            LOG.info('Periodic consistency check..')

            old_deleted_entities = self._find_old_deleted_entities()
            if old_deleted_entities:
                LOG.info('Consistency will remove %s deleted entities',
                         len(old_deleted_entities))
                LOG.debug('Consistency entities to remove: %s',
                          old_deleted_entities)
            self._push_events_to_queue(old_deleted_entities,
                                       GraphAction.REMOVE_DELETED_ENTITY)

            stale_entities = self._find_outdated_entities_to_mark_as_deleted()
            if stale_entities:
                LOG.info('Consistency will mark %s entities as deleted',
                         len(stale_entities))
                LOG.debug('Consistency entities to mark deleted: %s',
                          stale_entities)
            self._push_events_to_queue(stale_entities,
                                       GraphAction.DELETE_ENTITY)
            LOG.info('Periodic consistency check done.')
        except Exception:
            LOG.exception('Error in deleting vertices from entity_graph.')

    def _find_outdated_entities_to_mark_as_deleted(self):
        vitrage_sample_tstmp = str(utcnow() - timedelta(
            seconds=2 * self.conf.datasources.snapshots_interval))
        query = {
            'and': [
                {'!=': {VProps.VITRAGE_TYPE: VITRAGE_DATASOURCE}},
                {'<': {VProps.VITRAGE_SAMPLE_TIMESTAMP: vitrage_sample_tstmp}},
                {'==': {VProps.VITRAGE_IS_DELETED: False}},
            ]
        }

        vertices = self.graph.get_vertices(query_dict=query)
        return set(self._filter_vertices_to_be_marked_as_deleted(vertices))

    def _find_old_deleted_entities(self):
        vitrage_sample_tstmp = str(utcnow() - timedelta(
            seconds=self.conf.consistency.min_time_to_delete))
        query = {
            'and': [
                {'==': {VProps.VITRAGE_IS_DELETED: True}},
                {'<': {VProps.VITRAGE_SAMPLE_TIMESTAMP: vitrage_sample_tstmp}}
            ]
        }

        vertices = self.graph.get_vertices(query_dict=query)

        return self._filter_vertices_to_be_deleted(vertices)

    def _push_events_to_queue(self, vertices, action):
        events = []
        for vertex in vertices:
            event = {
                DSProps.ENTITY_TYPE: CONSISTENCY_DATASOURCE,
                DSProps.DATASOURCE_ACTION: DatasourceAction.UPDATE,
                DSProps.SAMPLE_DATE: str(utcnow()),
                DSProps.EVENT_TYPE: action,
                VProps.VITRAGE_ID: vertex[VProps.VITRAGE_ID],
                VProps.ID: vertex.get(VProps.ID, None),
                VProps.VITRAGE_TYPE: vertex[VProps.VITRAGE_TYPE],
                VProps.VITRAGE_CATEGORY: vertex[VProps.VITRAGE_CATEGORY],
                VProps.IS_REAL_VITRAGE_ID: True
            }
            events.append(event)
        self.actions_callback('consistency', events)

    @staticmethod
    def _filter_vertices_to_be_deleted(vertices):
        return list(filter(
            lambda ver:
            not (ver[VProps.VITRAGE_CATEGORY] == EntityCategory.RESOURCE and
                 ver[VProps.VITRAGE_TYPE] == OPENSTACK_CLUSTER), vertices))

    def _filter_vertices_to_be_marked_as_deleted(self, vertices):
        return list(filter(self._should_delete_vertex, vertices))

    def _should_delete_vertex(self, vertex):
        """Decide which vertices should be deleted by the consistency

        - delete all placeholder vertices, except from the openstack.cluster
        - delete vertices that their datasource is in the list
        """
        return (vertex.get(VProps.VITRAGE_IS_PLACEHOLDER) and
                not vertex[VProps.VITRAGE_TYPE] == OPENSTACK_CLUSTER) or \
               (vertex.get(VProps.VITRAGE_DATASOURCE_NAME) in
                self.datasources_to_mark_deleted)

    def _init_datasources_to_mark_deleted(self):
        self.datasources_to_mark_deleted = []

        for driver_name in self.conf.datasources.types:
            driver_class = utils.get_driver_class(self.conf, driver_name)
            if driver_class.should_delete_outdated_entities():
                self.datasources_to_mark_deleted.append(driver_name)

        if self.datasources_to_mark_deleted:
            LOG.info('Vertices of the following datasources will be deleted if'
                     'they become outdated: %s',
                     self.datasources_to_mark_deleted)
