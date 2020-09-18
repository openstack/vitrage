# Copyright 2016 - Nokia, ZTE
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR  CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from functools import reduce
from itertools import chain
from jsonschema import validate

from oslo_config import cfg
from oslo_log import log

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import GraphAction
from vitrage.datasources.driver_base import DriverBase
from vitrage.datasources.static import STATIC_DATASOURCE
from vitrage.datasources.static import STATIC_SCHEMA
from vitrage.datasources.static import StaticFields
from vitrage.utils import file as file_utils

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class StaticDriver(DriverBase):
    # base fields are required for all entities, others are treated as metadata
    BASE_FIELDS = {StaticFields.STATIC_ID,
                   StaticFields.TYPE,
                   StaticFields.ID}

    def __init__(self):
        super(StaticDriver, self).__init__()
        self.entities_cache = []

    @staticmethod
    def _is_valid_config(config, path):
        """check for validity of configuration"""
        try:
            validate(config, STATIC_SCHEMA)
            return True
        except Exception:
            msg = "Invalid config file: %s" % path
            LOG.exception(msg)
            return False

    @staticmethod
    def get_event_types():
        return []

    def enrich_event(self, event, event_type):
        pass

    def get_all(self, datasource_action):
        return self.make_pickleable(self._get_and_cache_all_entities(),
                                    STATIC_DATASOURCE,
                                    datasource_action)

    def get_changes(self, datasource_action):
        return self.make_pickleable(self._get_and_cache_changed_entities(),
                                    STATIC_DATASOURCE,
                                    datasource_action)

    @staticmethod
    def should_delete_outdated_entities():
        return True

    def _get_and_cache_all_entities(self):
        self.entities_cache = self._get_all_entities()
        return self.entities_cache

    def _get_all_entities(self):
        files = file_utils.list_files(CONF.static.directory, '.yaml', True)
        return list(reduce(chain, [self._get_entities_from_file(path)
                                   for path in files], []))

    def _get_and_cache_changed_entities(self):
        changed_entities = []
        new_entities = self._get_all_entities()

        for new_entity in new_entities:
            old_entity = self._find_entity(new_entity, self.entities_cache)

            if old_entity:
                # Add modified entities
                if not self._equal_entities(old_entity, new_entity):
                    changed_entities.append(new_entity.copy())
            else:
                # Add new entities
                changed_entities.append(new_entity.copy())

        # Add deleted entities
        for old_entity in self.entities_cache:
            if not self._find_entity(old_entity, new_entities):
                old_entity_copy = old_entity.copy()
                old_entity_copy[DSProps.EVENT_TYPE] = GraphAction.DELETE_ENTITY
                changed_entities.append(old_entity_copy)

        self.entities_cache = new_entities
        return changed_entities

    @classmethod
    def _get_entities_from_file(cls, path):
        config = file_utils.load_yaml_file(path)

        if not cls._is_valid_config(config, path):
            return []

        definitions = config[StaticFields.DEFINITIONS]

        entities = definitions[StaticFields.ENTITIES]
        relationships = definitions[StaticFields.RELATIONSHIPS]

        return cls._pack(entities, relationships)

    @classmethod
    def _pack(cls, entities, relationships):
        entities_dict = {}
        for entity in entities:
            cls._pack_entity(entities_dict, entity)
        for rel in relationships:
            cls._pack_rel(entities_dict, rel)
        return entities_dict.values()

    @classmethod
    def _pack_entity(cls, entities_dict, entity):
        static_id = entity[StaticFields.STATIC_ID]
        if static_id not in entities_dict:
            metadata = {key: value for key, value in entity.items()
                        if key not in cls.BASE_FIELDS}
            entities_dict[static_id] = entity
            entity[StaticFields.RELATIONSHIPS] = []
            entity[StaticFields.METADATA] = metadata
        else:
            LOG.warning("Skipped duplicated entity: {}".format(entity))

    @classmethod
    def _pack_rel(cls, entities_dict, rel):
        source_id = rel[StaticFields.SOURCE]
        target_id = rel[StaticFields.TARGET]

        if source_id == target_id:
            # self pointing relationship
            entities_dict[source_id][StaticFields.RELATIONSHIPS].append(rel)
        else:
            source, target = entities_dict[source_id], entities_dict[target_id]
            source[StaticFields.RELATIONSHIPS].append(
                cls._expand_neighbor(rel, target))

    @staticmethod
    def _expand_neighbor(rel, neighbor):
        """Expand config id to neighbor entity

        rel={'source': 's1', 'target': 'r1', 'relationship_type': 'attached'}
        neighbor={'static_id': 'h1', 'vitrage_type': 'host.nova', 'id': 1}
        result={'relationship_type': 'attached', 'source': 's1',
                'target': {'static_id': 'h1',
                           'vitrage_type': 'host.nova',
                           'id': 1}}
        """

        rel = rel.copy()
        if rel[StaticFields.SOURCE] == neighbor[StaticFields.STATIC_ID]:
            rel[StaticFields.SOURCE] = neighbor
        elif rel[StaticFields.TARGET] == neighbor[StaticFields.STATIC_ID]:
            rel[StaticFields.TARGET] = neighbor
        else:
            # TODO(yujunz) raise exception and ignore invalid relationship
            LOG.error("Invalid neighbor {} for relationship {}"
                      .format(neighbor, rel))
            return None
        return rel

    @staticmethod
    def _find_entity(search_entity, entities):
        # naive implementation since we don't expect many static entities
        for entity in entities:
            if entity[StaticFields.TYPE] == search_entity[StaticFields.TYPE] \
                    and entity[StaticFields.ID] == \
                    search_entity[StaticFields.ID]:
                return entity

    @staticmethod
    def _equal_entities(old_entity, new_entity):
        # TODO(iafek): compare also the relationships
        return old_entity.get(StaticFields.TYPE) == \
            new_entity.get(StaticFields.TYPE) and \
            old_entity.get(StaticFields.ID) == \
            new_entity.get(StaticFields.ID) and \
            old_entity.get(StaticFields.NAME) == \
            new_entity.get(StaticFields.NAME) and \
            old_entity.get(StaticFields.STATE) == \
            new_entity.get(StaticFields.STATE)
