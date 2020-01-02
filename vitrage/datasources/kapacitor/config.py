# Copyright 2019 - Viettel
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

import re

from oslo_config import cfg
from oslo_log import log

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.utils import file as file_utils

CONF = cfg.CONF
LOG = log.getLogger(__name__)
KAPACITOR_HOST = 'kapacitor_host'
KAPACITOR = 'kapacitor'
HOST = 'host'
TYPE = 'type'
NAME = 'name'
ALERT = 'alert'
VITRAGE_RESOURCE = 'vitrage_resource'


class KapacitorConfig(object):
    def __init__(self):
        try:
            kapacitor_config_file = CONF.kapacitor[DSOpts.CONFIG_FILE]
            kapacitor_config = file_utils.load_yaml_file(kapacitor_config_file)
            kapacitor = kapacitor_config[KAPACITOR]

            self.mappings = [self._create_mapping(config)
                             for config in kapacitor]
        except Exception:
            LOG.exception('Failed in init.')
            self.mappings = []

    @staticmethod
    def _create_mapping(config):
        return KapacitorHostMapping(config[ALERT][HOST],
                                    config[VITRAGE_RESOURCE][TYPE],
                                    config[VITRAGE_RESOURCE][NAME])

    def get_vitrage_resource(self, kapacitor_host):
        """Get Resource type and name for the given kapacitor host name

        Go over the configuration mappings one by one, and return the resource
        by the first mapping that applies to kapacitor host name.

        :param kapacitor_host: kapacitor host name
        :return: Vitrage (resource type, resource name)
        """
        for mapping in self.mappings:
            mapped_resource = mapping.map(kapacitor_host)
            if mapped_resource:
                return mapped_resource

        return None


class KapacitorHostMapping(object):
    KAPACITOR_HOST_NAME = '${' + KAPACITOR_HOST + '}'

    def __init__(self, kapacitor_host_regexp, resource_type, resource_name):
        self.kapacitor_host_regexp = re.compile(kapacitor_host_regexp)
        self.resource_type = resource_type
        self.resource_name = resource_name

    def map(self, kapacitor_host):
        """Check if the mapping applies to this service

        :param kapacitor_host: kapacitor host name
        :return: a tuple of (resource type, resource name)
        In case kapacitor_host_regexp is ${kapacitor_host},
        return kapacitor host name as the resource name
        """

        if kapacitor_host and self.kapacitor_host_regexp.match(kapacitor_host):
            resource_name = kapacitor_host\
                if self.resource_name == self.KAPACITOR_HOST_NAME \
                else self.resource_name
            return self.resource_type, resource_name
        else:
            return None
