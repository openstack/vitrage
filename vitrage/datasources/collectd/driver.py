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

from oslo_config import cfg
from oslo_log import log

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.datasources.alarm_driver_base import AlarmDriverBase
from vitrage.datasources.collectd import COLLECTD_DATASOURCE
from vitrage.datasources.collectd.mapper import CollectdMapper
from vitrage.datasources.collectd.properties\
    import CollectdProperties as CProps
from vitrage.utils import file as file_utils

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class CollectdDriver(AlarmDriverBase):
    conf_map = None

    def __init__(self):
        super(CollectdDriver, self).__init__()
        if not CollectdDriver.conf_map:
            mapper = CollectdDriver._configuration_mapping()
            if mapper:
                CollectdDriver.conf_map = CollectdMapper(mapper)

    def _vitrage_type(self):
        return COLLECTD_DATASOURCE

    def _alarm_key(self, alarm):
        return alarm[CProps.ID]

    def _get_alarms(self):
        return []

    def _is_erroneous(self, alarm):
        return alarm and alarm[CProps.SEVERITY] != 'OK'

    def _status_changed(self, new_alarm, old_alarm):
        return new_alarm and old_alarm \
            and not new_alarm[CProps.SEVERITY] == old_alarm[CProps.SEVERITY]

    def _is_valid(self, alarm):
        return alarm[CProps.RESOURCE_TYPE] is not None \
            and alarm[CProps.RESOURCE_NAME] is not None

    @staticmethod
    def _configuration_mapping():
        try:
            collectd_config_file = CONF.collectd[DSOpts.CONFIG_FILE]
            collectd_config = file_utils.load_yaml_file(collectd_config_file)
            collectd_config_elements = collectd_config[COLLECTD_DATASOURCE]

            mappings = {}
            for element_config in collectd_config_elements:
                mappings[element_config['collectd_host']] = {
                    CProps.RESOURCE_TYPE: element_config['type'],
                    CProps.RESOURCE_NAME: element_config['name']
                }

            LOG.debug('collectd mappings: %s', mappings)

            return mappings
        except Exception:
            LOG.exception('Failed in init.')
            return {}

    def enrich_event(self, event, event_type):
        event[DSProps.EVENT_TYPE] = event_type

        if CollectdDriver.conf_map:
            # PLUGIN_INSTANCE is optional
            resources = [event[CProps.HOST], event[CProps.PLUGIN],
                         event.get(CProps.PLUGIN_INSTANCE)]
            resource = '/'.join([resource for resource in resources if
                                 resource])
            v_resource = CollectdDriver.conf_map.find(resource)
            event[CProps.RESOURCE_NAME] = v_resource[CProps.RESOURCE_NAME]
            event[CProps.RESOURCE_TYPE] = v_resource[CProps.RESOURCE_TYPE]

        return CollectdDriver.make_pickleable([event], COLLECTD_DATASOURCE,
                                              DatasourceAction.UPDATE)[0]

    @staticmethod
    def get_event_types():
        return ['collectd.alarm.ok',
                'collectd.alarm.failure',
                'collectd.alarm.warning']

    @staticmethod
    def should_delete_outdated_entities():
        return True
