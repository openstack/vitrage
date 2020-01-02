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

import os

from oslo_config import cfg
from oslo_log import log

from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.entity_graph.mappings.alarm_handler import AlarmHandler
from vitrage.entity_graph.mappings.resource_handler import \
    ResourceHandler
from vitrage.utils import file as file_utils

CONF = cfg.CONF
LOG = log.getLogger(__name__)


DEFAULT_INFO_MAPPER = 'default'


class DatasourceInfoMapper(object):
    OPERATIONAL_VALUES = 'operational_values'
    PRIORITY_VALUES = 'priority_values'
    UNDEFINED_DATASOURCE = 'undefined datasource'

    def __init__(self):
        self.category_normalizer = self._init_category_normalizer()
        self.datasources_value_confs = self._load_value_configurations()

    def vitrage_operational_value(self, vitrage_type, value):
        return self._get_value_data(vitrage_type,
                                    value,
                                    self.OPERATIONAL_VALUES)

    def value_priority(self, vitrage_type, value):
        return self._get_value_data(vitrage_type,
                                    value,
                                    self.PRIORITY_VALUES)

    def vitrage_aggregate_values(self, new_vertex, graph_vertex):
        LOG.debug('new_vertex: %s', new_vertex)
        LOG.debug('graph_vertex: %s', graph_vertex)

        vitrage_type = new_vertex[VProps.VITRAGE_TYPE] if \
            VProps.VITRAGE_TYPE in new_vertex.properties else \
            graph_vertex[VProps.VITRAGE_TYPE]

        vitrage_category = new_vertex[VProps.VITRAGE_CATEGORY] if \
            VProps.VITRAGE_CATEGORY in new_vertex.properties else \
            graph_vertex[VProps.VITRAGE_CATEGORY]

        if vitrage_type in self.datasources_value_confs or \
                vitrage_type not in CONF.datasources.types:
            value_properties = \
                self.category_normalizer[vitrage_category].value_properties()
            vitrage_oper_value, vitrage_aggregated_value, value_priority = \
                self._find_operational_value_and_priority(new_vertex,
                                                          graph_vertex,
                                                          value_properties[0],
                                                          vitrage_type)
            value_properties.pop(0)

            for property_ in value_properties:
                t_operational_value, t_aggregated_value, t_value_priority = \
                    self._find_operational_value_and_priority(new_vertex,
                                                              graph_vertex,
                                                              property_,
                                                              vitrage_type)
                if t_value_priority > value_priority:
                    vitrage_oper_value = t_operational_value
                    vitrage_aggregated_value = t_aggregated_value
                    value_priority = t_value_priority

            self.category_normalizer[vitrage_category].set_aggregated_value(
                new_vertex, vitrage_aggregated_value)
            self.category_normalizer[vitrage_category].set_operational_value(
                new_vertex, vitrage_oper_value)
        else:
            self.category_normalizer[vitrage_category].set_aggregated_value(
                new_vertex, self.UNDEFINED_DATASOURCE)
            self.category_normalizer[vitrage_category].set_operational_value(
                new_vertex, self.UNDEFINED_DATASOURCE)

    def get_datasource_priorities(self, vitrage_type=None):
        if vitrage_type:
            datasource_info = self.datasources_value_confs[vitrage_type]
            return datasource_info[self.PRIORITY_VALUES]
        else:
            priorities_dict = \
                {key: self.datasources_value_confs[key][self.PRIORITY_VALUES]
                 for key in self.datasources_value_confs.keys()}
            return priorities_dict

    @staticmethod
    def _init_category_normalizer():
        return {
            EntityCategory.RESOURCE: ResourceHandler(),
            EntityCategory.ALARM: AlarmHandler()
        }

    def _load_value_configurations(self):
        valid_datasources_conf = {}
        erroneous_datasources_conf = []

        files = file_utils.list_files(
            CONF.entity_graph.datasources_values_dir, '.yaml')

        for file_name in files:
            try:
                full_path = CONF.entity_graph.datasources_values_dir \
                    + '/' + file_name
                operational_values, priority_values = \
                    self._retrieve_values_and_priorities_from_file(full_path)
                valid_datasources_conf[os.path.splitext(file_name)[0]] = {
                    self.OPERATIONAL_VALUES: operational_values,
                    self.PRIORITY_VALUES: priority_values
                }
            except Exception:
                datasource = os.path.splitext(file_name)[0]
                erroneous_datasources_conf.append(datasource)
                LOG.exception('Erroneous data source is %s', datasource)

        self._check_value_confs_exists(
            [key for key in valid_datasources_conf.keys()],
            erroneous_datasources_conf)

        return valid_datasources_conf

    def _retrieve_values_and_priorities_from_file(self, full_path):
        values = {}
        priorities = {}
        config = file_utils.load_yaml_file(full_path, with_exception=True)
        vitrage_category = config['category']

        for item in config['values']:
            aggregated_values = item['aggregated values']
            priority_value = int(aggregated_values['priority'])

            # original to operational value
            for value_map in aggregated_values['original values']:
                name = value_map['name']
                operational_value = value_map['operational_value']
                values[name.upper()] = operational_value
                priorities[name.upper()] = priority_value

        self._check_validity(vitrage_category, values, priorities, full_path)

        self._add_default_values(values, priorities, vitrage_category)

        return values, priorities

    def _add_default_values(self, values, priorities, category):
        default_values = self.category_normalizer[category].default_values()
        for original_val, operational_val, priority_val in default_values:
            values[original_val] = operational_val
            priorities[original_val] = priority_val

    def _check_validity(self, category, values, priorities, full_path):
        # check that all the operational values exists
        state_class_instance = \
            self.category_normalizer[category].get_value_class_instance()
        operational_values = DatasourceInfoMapper.\
            _get_all_local_variables_of_class(state_class_instance)
        for operational_value in values.values():
            if operational_value not in operational_values:
                raise ValueError('operational value %s for %s is not in %s',
                                 operational_value, full_path,
                                 state_class_instance.__class__.__name__)

    def _get_value_data(self, vitrage_type, value, data_type):
        try:
            upper_value = value if not value else value.upper()

            if vitrage_type in self.datasources_value_confs:
                values_conf = self.datasources_value_confs[
                    vitrage_type][data_type]

                return values_conf[upper_value] if upper_value in values_conf \
                    else values_conf[None]
            else:
                values_conf = self.datasources_value_confs[
                    DEFAULT_INFO_MAPPER][data_type]

                return values_conf[upper_value] if upper_value in values_conf \
                    else values_conf[None]
        except Exception:
            LOG.error('Exception in datasource: %s', vitrage_type)
            raise

    def _find_operational_value_and_priority(self,
                                             new_vertex,
                                             graph_vertex,
                                             property_,
                                             vitrage_type):
        state = self._get_updated_property(new_vertex,
                                           graph_vertex,
                                           property_)

        upper_state = state if not state else state.upper()

        vitrage_operational_state = self.vitrage_operational_value(
            vitrage_type, upper_state)

        value_priority = self.value_priority(vitrage_type,
                                             upper_state)

        return vitrage_operational_state, upper_state, value_priority

    @staticmethod
    def _get_all_local_variables_of_class(class_instance):
        return [getattr(class_instance, attr) for attr in dir(class_instance)
                if not callable(attr) and not attr.startswith("__")]

    def _check_value_confs_exists(self,
                                  ok_datasources,
                                  error_datasources):

        datasource_types = CONF.datasources.types
        datasources_with_state_conf = ok_datasources + error_datasources

        for datasource_type in datasource_types:
            if datasource_type not in datasources_with_state_conf:
                LOG.info("No state configuration file for: %s",
                         datasource_type)

    @staticmethod
    def _get_updated_property(new_vertex, graph_vertex, prop):
        if new_vertex and prop in new_vertex.properties:
            return new_vertex[prop]
        elif graph_vertex and prop in graph_vertex.properties:
            return graph_vertex[prop]

        return None
