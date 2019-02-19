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

from oslo_log import log

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import GraphAction
from vitrage.datasources.driver_base import DriverBase
from vitrage.utils import datetime as datetime_utils

LOG = log.getLogger(__name__)


class AlarmDriverBase(DriverBase):
    def __init__(self):
        super(DriverBase, self).__init__()
        self.cache = dict()

    def _vitrage_type(self):
        """Return the vitrage_type of the datasource """
        pass

    def _alarm_key(self, alarm):
        """Return a unique key of the alarm, to identify it in the cache """
        pass

    def _get_alarms(self):
        """Return the list of alarms of this plugin """
        pass

    def _enrich_alarms(self, alarms):
        """Optionally add more data to the alarms

        :param alarms: list of alarms to be enriched
        :return:
        """
        pass

    def _is_erroneous(self, alarm):
        """Check if the state of the alarm is erroneous

        :param alarm:
        :return: True/False based on the alarm state
        """
        pass

    def _status_changed(self, new_alarm, old_alarm):
        """Check if the status of the two alarms is different

        :param alarm1:
        :param alarm2:
        :return: True/False based on the alarms states
        """
        pass

    def _is_valid(self, alarm):
        """Check if the alarm is valid

        :param alarm: an alarm to check
        :return: True/False
        """
        pass

    def get_all(self, datasource_action):
        return self.make_pickleable(self._get_all_alarms(),
                                    self._vitrage_type(),
                                    datasource_action)

    def get_changes(self, datasource_action):
        return self.make_pickleable(self._get_changed_alarms(),
                                    self._vitrage_type(),
                                    datasource_action)

    def _get_all_alarms(self):
        alarms = self._get_alarms()
        self._enrich_alarms(alarms)
        return self._filter_and_cache_alarms(
            alarms,
            self._filter_get_erroneous)

    def _get_changed_alarms(self):
        alarms = self._get_alarms()
        self._enrich_alarms(alarms)
        return self._filter_and_cache_alarms(
            alarms,
            self._filter_get_change)

    def _filter_and_cache_alarms(self, alarms, filter_):
        alarms_to_update = []
        now = datetime_utils.utcnow(False)

        for alarm in alarms:
            alarm_key = self._alarm_key(alarm)
            old_alarm = self.cache.get(alarm_key, (None, None))[0]
            if self._filter_and_cache_alarm(alarm, old_alarm, filter_, now):
                alarms_to_update.append(alarm)

        # add alarms that were deleted
        # (i.e. the alarm definition was deleted from the datasource)
        values = list(self.cache.values())
        for cached_alarm, timestamp in values:
            if self._is_erroneous(cached_alarm) and timestamp is not now:
                LOG.debug('deleting cached_alarm %s', cached_alarm)
                cached_alarm[DSProps.EVENT_TYPE] = GraphAction.DELETE_ENTITY
                alarms_to_update.append(cached_alarm)
                self.cache.pop(self._alarm_key(cached_alarm))

        return alarms_to_update

    def _filter_get_valid(self, alarm, _):
        return alarm if self._is_valid(alarm) else None

    def _filter_get_erroneous(self, alarm, old_alarm):
        return alarm \
            if self._is_valid(alarm) and \
            (self._is_erroneous(alarm) or self._is_erroneous(old_alarm)) \
            else None

    def _filter_get_change(self, alarm, old_alarm):
        if not self._is_valid(alarm):
            return None
        if self._status_changed(alarm, old_alarm):
            return alarm
        elif not old_alarm and self._is_erroneous(alarm):
            return alarm
        else:
            return None

    def _filter_and_cache_alarm(self, alarm, old_alarm, filter_, time):
        ret = alarm if filter_(alarm, old_alarm) else None
        self.cache[self._alarm_key(alarm)] = alarm, time
        return ret

    def _old_alarm(self, event):
        alarm_key = self._alarm_key(event)
        return self.cache.get(alarm_key, (None, None))[0]
