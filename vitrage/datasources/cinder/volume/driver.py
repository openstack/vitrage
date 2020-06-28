# Copyright 2016 - Alcatel-Lucent
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,  software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND,  either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.datasources.cinder.volume import CINDER_VOLUME_DATASOURCE
from vitrage.datasources.driver_base import DriverBase
from vitrage import os_clients


class CinderVolumeDriver(DriverBase):

    def __init__(self):
        super(CinderVolumeDriver, self).__init__()
        self._client = None

    @property
    def client(self):
        if not self._client:
            self._client = os_clients.cinder_client()
        return self._client

    @staticmethod
    def extract_events(volumes):
        return [vars(volume) for volume in volumes]

    def get_all(self, datasource_action):
        return self.make_pickleable(
            self.extract_events(self.client.volumes.list(
                search_opts={'all_tenants': 1})),
            CINDER_VOLUME_DATASOURCE,
            datasource_action,
            *self.properties_to_filter_out())

    def enrich_event(self, event, event_type):
        event[DSProps.EVENT_TYPE] = event_type

        return CinderVolumeDriver.make_pickleable([event],
                                                  CINDER_VOLUME_DATASOURCE,
                                                  DatasourceAction.UPDATE)[0]

    @staticmethod
    def properties_to_filter_out():
        return ['manager']

    @staticmethod
    def get_event_types():
        return ['volume.create.start',
                'volume.create.end',
                'volume.attach.start',
                'volume.attach.end',
                'volume.detach.start',
                'volume.detach.end',
                'volume.delete.start',
                'volume.delete.end']

    @staticmethod
    def should_delete_outdated_entities():
        return True
