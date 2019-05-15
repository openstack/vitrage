# Copyright 2018 - Vitrage team
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

from oslo_log import log

from vitrage.datasources.driver_base import DriverBase
from vitrage.datasources.sample import SAMPLE_DATASOURCE

LOG = log.getLogger(__name__)


class SampleDriver(DriverBase):

    def __init__(self):
        super(SampleDriver, self).__init__()

    @staticmethod
    def get_event_types():
        return []

    def enrich_event(self, event, event_type):
        pass

    def get_all(self, datasource_action):
        """Query all entities and send events to the vitrage events queue.

        When done for the first time, send an "end" event to inform it has
        finished the get_all for the datasource (because it is done
        asynchronously).
        """

        return self.make_pickleable(self._get_all_entities(),
                                    SAMPLE_DATASOURCE,
                                    datasource_action)

    def get_changes(self, datasource_action):
        """Send an event to the vitrage events queue upon any change."""

        return self.make_pickleable(self._get_changes_entities(),
                                    SAMPLE_DATASOURCE,
                                    datasource_action)

    def _get_all_entities(self):
        return []

    def _get_changes_entities(self):
        return []
