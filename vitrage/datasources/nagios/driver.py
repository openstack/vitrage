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
import requests

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.datasources.alarm_driver_base import AlarmDriverBase
from vitrage.datasources.nagios.config import NagiosConfig
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources.nagios.parser import NagiosParser
from vitrage.datasources.nagios.properties import NagiosProperties\
    as NagiosProps
from vitrage.datasources.nagios.properties import NagiosTestStatus

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class NagiosDriver(AlarmDriverBase):
    ServiceKey = namedtuple('ServiceKey', ['hostname', 'service'])

    def __init__(self):
        super(NagiosDriver, self).__init__()
        self.config = NagiosConfig()

    def _vitrage_type(self):
        return NAGIOS_DATASOURCE

    def _alarm_key(self, alarm):
        return self.ServiceKey(hostname=alarm[NagiosProps.RESOURCE_NAME],
                               service=alarm[NagiosProps.SERVICE])

    def _get_alarms(self):
        nagios_user = CONF.nagios.user
        nagios_password = CONF.nagios.password
        nagios_url = CONF.nagios.url

        if not nagios_user:
            return []

        if not nagios_password:
            LOG.warning('Nagios password is not defined')
            return []

        if not nagios_url:
            LOG.warning('Nagios url is not defined')
            return []

        session = requests.Session()
        payload = {'host': 'all', 'limit': '0'}

        response = session.get(nagios_url,
                               params=payload,
                               auth=(nagios_user, nagios_password))

        if response.status_code == requests.codes.ok:
            nagios_services = NagiosParser().parse(response.text)
            return nagios_services
        else:
            LOG.error('Failed to get nagios data. Response code: %s',
                      response.status_code)
            return []

    def _enrich_alarms(self, alarms):
        for alarm in alarms:
            # based on nagios configuration file, convert nagios host name
            # to vitrage resource type and name
            alarm[DSProps.ENTITY_TYPE] = NagiosProps.NAGIOS

            nagios_host = alarm[NagiosProps.RESOURCE_NAME]
            vitrage_resource = self.config.get_vitrage_resource(nagios_host)

            alarm[NagiosProps.RESOURCE_TYPE] = \
                vitrage_resource[0] if vitrage_resource else None
            alarm[NagiosProps.RESOURCE_NAME] = \
                vitrage_resource[1] if vitrage_resource else None

    def _is_erroneous(self, alarm):
        return alarm and alarm[NagiosProps.STATUS] != NagiosTestStatus.OK

    def _status_changed(self, alarm1, alarm2):
        return alarm1 and alarm2 and \
            not alarm1[NagiosProps.STATUS] == alarm2[NagiosProps.STATUS]

    def _is_valid(self, alarm):
        return alarm[NagiosProps.RESOURCE_TYPE] is not None and \
            alarm[NagiosProps.RESOURCE_NAME] is not None

    @staticmethod
    def should_delete_outdated_entities():
        return True
