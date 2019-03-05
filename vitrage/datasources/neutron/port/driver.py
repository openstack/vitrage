# Copyright 2016 - Alcatel-Lucent
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,  software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND,  either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from oslo_log import log

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.datasources.neutron.base import NeutronBase
from vitrage.datasources.neutron.port import NEUTRON_PORT_DATASOURCE


LOG = log.getLogger(__name__)


# noinspection PyAbstractClass
class PortDriver(NeutronBase):

    @staticmethod
    def get_event_types():
        return ['port.create.end',
                'port.update.end',
                'port.delete.end']

    def enrich_event(self, event, event_type):
        if 'compute' not in event.get('port', {}).get('device_owner', ''):
            LOG.debug('Ignoring this event the port '
                      'is not connected to a compute: %s', event)
            return []

        event[DSProps.EVENT_TYPE] = event_type
        enriched_event = \
            PortDriver.make_pickleable([event], NEUTRON_PORT_DATASOURCE,
                                       DatasourceAction.UPDATE)[0]
        return enriched_event

    @staticmethod
    def properties_to_filter_out():
        """Return a list of properties to be removed from the event"""
        return ['manager', '_info']

    def get_all(self, datasource_action):
        ports = self.client.list_ports()['ports']
        ports = [p for p in ports if 'compute' in p.get('device_owner', '')]
        return self.make_pickleable(
            ports,
            NEUTRON_PORT_DATASOURCE,
            datasource_action,
            *self.properties_to_filter_out())

    @staticmethod
    def should_delete_outdated_entities():
        return True
