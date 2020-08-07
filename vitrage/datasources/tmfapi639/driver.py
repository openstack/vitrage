# Copyright 2020
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
import requests

from vitrage.datasources.driver_base import DriverBase
from vitrage.datasources.tmfapi639.config import TmfApi639Config
from vitrage.datasources.tmfapi639 import TMFAPI639_DATASOURCE

LOG = log.getLogger(__name__)


class TmfApi639Driver(DriverBase):

    def __init__(self):
        super(TmfApi639Driver, self).__init__()
        self.config = TmfApi639Config()
        self.endpoints = self.config.endpoints
        self.event_lambda = 0

    @staticmethod
    def get_event_types():
        return ['tmfapi639.instance.create',
                'tmfapi639.instance.update',
                'tmfapi639.instance.delete']

    def enrich_event(self, event, event_type):
        pass

    def get_all(self, datasource_action):
        """Query all entities and send events to the vitrage events queue.

        When done for the first time, send an "end" event to inform it has
        finished the get_all for the datasource (because it is done
        asynchronously).
        """
        return self.make_pickleable(self._get_all_entities(),
                                    TMFAPI639_DATASOURCE,
                                    datasource_action)

    def get_changes(self, datasource_action):
        """Send an event to the vitrage events queue upon any change."""
        return self.make_pickleable(self._get_changes_entities(),
                                    TMFAPI639_DATASOURCE,
                                    datasource_action)

    def _get_all_entities(self):
        total = []
        for pairs in self.endpoints:
            try:
                if isinstance(pairs, str):  # Doesn't contain update URL
                    LOG.info("Connecting to " + pairs)
                    pairs = (pairs, "")
                r = requests.get(pairs[0])
                total += r.json()
            except Exception as e:
                LOG.error("Couldn't establish connection:" + str(e))
        return total

    def _get_changes_entities(self):  # Called by get changes
        total = []
        for pairs in self.endpoints:
            try:
                if isinstance(pairs, tuple):  # Contains an update URL
                    LOG.info("Connecting to " + pairs[0] +
                             "with updates in " + pairs[1])
                    r = requests.get(pairs[1])
                    for e in r.json():
                        if e["eventId"] < self.event_lambda:
                            continue
                        total.append(e["event"]["resource"])
                        self.event_lambda = e["eventId"]
            except Exception as e:
                LOG.error("Couldn't establish connection:" + str(e))
        return total
