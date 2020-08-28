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

from collections import namedtuple

from oslo_config import cfg
from oslo_log import log
from oslo_utils import importutils as utils

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.datasources.alarm_driver_base import AlarmDriverBase
from vitrage.datasources.zabbix.properties import ZabbixProperties as ZProps
from vitrage.datasources.zabbix.properties import ZabbixTriggerStatus \
    as TriggerStatus
from vitrage.datasources.zabbix.properties import ZabbixTriggerValue \
    as TriggerValue
from vitrage.datasources.zabbix import ZABBIX_DATASOURCE
from vitrage.utils import file as file_utils

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class ZabbixDriver(AlarmDriverBase):
    ServiceKey = namedtuple('ServiceKey', ['hostname', 'triggerid'])
    conf_map = None

    def __init__(self):
        super(ZabbixDriver, self).__init__()
        if not ZabbixDriver.conf_map:
            ZabbixDriver.conf_map =\
                ZabbixDriver._configuration_mapping()
        self._client = None

    def zabbix_client_login(self):
        if not CONF.zabbix.user:
            LOG.warning('Zabbix user is not defined')
        if not CONF.zabbix.password:
            LOG.warning('Zabbix password is not defined')
        if not CONF.zabbix.url:
            LOG.warning('Zabbix url is not defined')

        try:
            if not self._client:
                self._client = utils.import_object(
                    'pyzabbix.ZabbixAPI',
                    CONF.zabbix.url)
            self._client.login(
                CONF.zabbix.user,
                CONF.zabbix.password)
        except Exception:
            LOG.exception('pyzabbix.ZabbixAPI error occurred.')
            self._client = None

    def _vitrage_type(self):
        return ZABBIX_DATASOURCE

    def _alarm_key(self, alarm):
        return self.ServiceKey(hostname=alarm[ZProps.RESOURCE_NAME],
                               triggerid=alarm[ZProps.TRIGGER_ID])

    def _get_alarms(self):
        self.zabbix_client_login()
        if not self._client:
            return []

        alarms = []
        valid_hosts = (host for host in
                       self._client.host.get(output=[ZProps.HOST])
                       if host[ZProps.HOST] in ZabbixDriver.conf_map)
        for host in valid_hosts:
            self._get_triggers_per_host(host, alarms)

        return alarms

    def _get_triggers_per_host(self, host, alarms):

        host_id = host[ZProps.HOST_ID]
        triggers = self._client.trigger.get(hostids=host_id,
                                            expandDescription=True)

        triggers_rawtexts = self._get_triggers_rawtexts(host_id)

        for trigger in triggers:
            trigger[ZProps.ZABBIX_RESOURCE_NAME] = host[ZProps.HOST]
            trigger_id = trigger[ZProps.TRIGGER_ID]
            trigger[ZProps.RAWTEXT] = triggers_rawtexts[trigger_id]
            alarms.append(trigger)

    def _get_triggers_rawtexts(self, host_id):

        output = [ZProps.TRIGGER_ID, ZProps.DESCRIPTION]
        triggers = self._client.trigger.get(hostids=host_id, output=output)

        return {trigger[ZProps.TRIGGER_ID]: trigger[ZProps.DESCRIPTION]
                for trigger in triggers}

    def _enrich_alarms(self, alarms):
        """Enrich zabbix alarm using zabbix configuration file

        converting Zabbix host name to Vitrage resource type and name

        :param alarms: Zabbix alarm
        :return: enriched alarm
        """

        for alarm in alarms:
            alarm[ZProps.VALUE] = self._get_value(alarm)

            zabbix_host = alarm[ZProps.ZABBIX_RESOURCE_NAME]
            vitrage_host = ZabbixDriver.conf_map[zabbix_host]
            alarm[ZProps.RESOURCE_TYPE] = vitrage_host[ZProps.RESOURCE_TYPE]
            alarm[ZProps.RESOURCE_NAME] = vitrage_host[ZProps.RESOURCE_NAME]

    def _is_erroneous(self, alarm):
        return alarm and \
            alarm[ZProps.VALUE] == TriggerValue.PROBLEM

    def _status_changed(self, new_alarm, old_alarm):

        if not (new_alarm and old_alarm):
            return False

        if new_alarm[ZProps.VALUE] != old_alarm[ZProps.VALUE]:
            return True

        if new_alarm[ZProps.VALUE] == TriggerValue.PROBLEM:
            priority_changed = \
                new_alarm[ZProps.PRIORITY] != old_alarm[ZProps.PRIORITY]
            description_changed = \
                new_alarm[ZProps.DESCRIPTION] != old_alarm[ZProps.DESCRIPTION]
            return priority_changed or description_changed

    def _is_valid(self, alarm):
        return alarm[ZProps.RESOURCE_TYPE] is not None and \
            alarm[ZProps.RESOURCE_NAME] is not None

    @staticmethod
    def _get_value(alarm):
        if alarm[ZProps.STATUS] == TriggerStatus.DISABLED:
            return TriggerValue.OK
        return alarm[ZProps.VALUE]

    @staticmethod
    def _configuration_mapping():
        try:
            zabbix_config_file = CONF.zabbix[DSOpts.CONFIG_FILE]
            zabbix_config = file_utils.load_yaml_file(zabbix_config_file)
            zabbix_config_elements = zabbix_config[ZABBIX_DATASOURCE]

            mappings = {}
            for element_config in zabbix_config_elements:
                mappings[element_config['zabbix_host']] = {
                    ZProps.RESOURCE_TYPE: element_config['type'],
                    ZProps.RESOURCE_NAME: element_config['name']
                }

            return mappings
        except Exception:
            LOG.exception('Failed in init.')
            return {}

    def enrich_event(self, event, event_type):
        event[DSProps.EVENT_TYPE] = event_type

        if ZabbixDriver.conf_map:
            zabbix_host = event[ZProps.HOST]
            event[ZProps.ZABBIX_RESOURCE_NAME] = zabbix_host
            v_resource = ZabbixDriver.conf_map[zabbix_host]
            event[ZProps.RESOURCE_NAME] = v_resource[ZProps.RESOURCE_NAME]
            event[ZProps.RESOURCE_TYPE] = v_resource[ZProps.RESOURCE_TYPE]

        return ZabbixDriver.make_pickleable([event], ZABBIX_DATASOURCE,
                                            DatasourceAction.UPDATE)[0]

    @staticmethod
    def get_event_types():
        return ['zabbix.alarm.ok', 'zabbix.alarm.problem']

    @staticmethod
    def should_delete_outdated_entities():
        return True
