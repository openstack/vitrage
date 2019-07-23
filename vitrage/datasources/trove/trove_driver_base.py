# Copyright 2018 Samsung Electronics
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import GraphAction
from vitrage.datasources.driver_base import DriverBase
from vitrage import os_clients


class TroveDriverBase(DriverBase):

    def __init__(self):
        super(TroveDriverBase, self).__init__()
        self.__client = None
        self.__cached_entities = []

    @property
    def client(self):
        if not self.__client:
            self.__client = os_clients.trove_client()
        return self.__client

    def get_all(self, datasource_action):
        return self.make_pickleable(self._get_and_cache_all_entities(),
                                    self._get_vitrage_type(),
                                    datasource_action,
                                    *self.properties_to_filter_out())

    def get_changes(self, datasource_action):
        return self.make_pickleable(self._get_changed_entities(),
                                    self._get_vitrage_type(),
                                    datasource_action,
                                    *self.properties_to_filter_out())

    def _get_and_cache_all_entities(self):
        self.__cached_entities = self._get_all_entities()
        return self.__cached_entities

    def _get_changed_entities(self):
        actual_entities = self._get_all_entities()
        changed_entities = []

        for actual_entity in actual_entities:
            cached_entity = self._find_entity(actual_entity,
                                              self.__cached_entities)
            if cached_entity:
                # Add modified entities
                if not self._equal_entities(actual_entity, cached_entity):
                    changed_entities.append(actual_entity)
            else:
                # Add new entities
                changed_entities.append(actual_entity)

        # Delete removed entities
        for cached_entity in self.__cached_entities:
            if not self._find_entity(cached_entity, actual_entities):
                cached_entity[DSProps.EVENT_TYPE] = GraphAction.DELETE_ENTITY
                changed_entities.append(cached_entity)

        self.__cached_entities = actual_entities
        return changed_entities

    @abc.abstractmethod
    def _get_vitrage_type(self):
        pass

    @abc.abstractmethod
    def _get_all_entities(self):
        pass

    @abc.abstractmethod
    def _find_entity(self, search_entity, entities):
        pass

    @abc.abstractmethod
    def _equal_entities(self, old_entity, new_entity):
        pass

    @staticmethod
    def properties_to_filter_out():
        return ['manager', '_info']

    @staticmethod
    def should_delete_outdated_entities():
        return True

    @staticmethod
    def extract_entities(entities):
        return [entity.to_dict() for entity in entities]
