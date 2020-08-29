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

from collections import namedtuple

from oslo_log import log

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.datasources.alarm_driver_base import AlarmDriverBase
from vitrage.datasources.kapacitor.config import KapacitorConfig
from vitrage.datasources.kapacitor import KAPACITOR_DATASOURCE
from vitrage.datasources.kapacitor.properties import KapacitorProperties \
    as KProps
from vitrage.datasources.kapacitor.properties import KapacitorState

LOG = log.getLogger(__name__)


class KapacitorDriver(AlarmDriverBase):
    ServiceKey = namedtuple('ServiceKey', ['hostname', 'alarmid'])
    conf_map = None

    def __init__(self):
        super(KapacitorDriver, self).__init__()

        if not KapacitorDriver.conf_map:
            self.conf_map = KapacitorConfig()
        self._client = None

    @staticmethod
    def get_event_types():
        return ['kapacitor.alarm.ok',
                'kapacitor.alarm.info',
                'kapacitor.alarm.warning',
                'kapacitor.alarm.critical']

    def _vitrage_type(self):
        return KAPACITOR_DATASOURCE

    def _alarm_key(self, alarm):
        return self.ServiceKey(hostname=alarm[KProps.RESOURCE_NAME],
                               alarmid=alarm[KProps.ID])

    def _enrich_alarms(self, alarms):
        """Enrich kapacitor alarm using kapacitor configuration file

        Converting Kapacitor host name to Vitrage resource type and name
        It is function of get_all for pulling method
        Not implement yet
        """
        pass

    def enrich_event(self, event, event_type):
        event[DSProps.EVENT_TYPE] = event_type

        kapacitor_host = event[KProps.HOST]
        vitrage_resource = self.conf_map.get_vitrage_resource(kapacitor_host)
        event[KProps.RESOURCE_TYPE] = \
            vitrage_resource[0] if vitrage_resource else None
        event[KProps.RESOURCE_NAME] = \
            vitrage_resource[1] if vitrage_resource else None
        return KapacitorDriver.make_pickleable([event], KAPACITOR_DATASOURCE,
                                               DatasourceAction.UPDATE)[0]

    def _is_erroneous(self, alarm):
        return alarm and alarm[KProps.PRIORITY] != KapacitorState.OK

    def _status_changed(self, new_alarm, old_alarm):
        return new_alarm and old_alarm and \
            not new_alarm[KProps.PRIORITY] == old_alarm[KProps.PRIORITY]

    def _is_valid(self, alarm):
        return alarm[KProps.RESOURCE_TYPE] is not None and \
            alarm[KProps.RESOURCE_NAME] is not None

    def _get_alarms(self):
        """Query all alarm and send to vitrage

        Not implement yet
        """
        return []

    @staticmethod
    def should_delete_outdated_entities():
        return True
