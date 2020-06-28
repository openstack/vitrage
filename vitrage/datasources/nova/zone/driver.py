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

from vitrage.datasources.nova.nova_driver_base import NovaDriverBase
from vitrage.datasources.nova.zone import NOVA_ZONE_DATASOURCE


class ZoneDriver(NovaDriverBase):

    @staticmethod
    def filter_internal_zone(zones):
        zones_res = []
        for zone in zones:
            zone_dict = vars(zone)
            if zone_dict['zoneName'] and zone_dict['zoneName'] != 'internal':
                zones_res.append(zone_dict)
        return zones_res

    def get_all(self, datasource_action):
        return self.make_pickleable(self.filter_internal_zone(
            self.client.availability_zones.list()),
            NOVA_ZONE_DATASOURCE,
            datasource_action,
            *self.properties_to_filter_out())

    @staticmethod
    def properties_to_filter_out():
        return ['manager', '_info']
