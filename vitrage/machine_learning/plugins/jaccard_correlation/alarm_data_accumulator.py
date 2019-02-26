# Copyright 2017 - Nokia
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

import datetime
from oslo_log import log

LOG = log.getLogger(__name__)


class AlarmDataAccumulator(object):

    def __init__(self, accumulated_data):
        self.active_start_times = {}
        self.alarms_activity = accumulated_data.activity
        # TODO(annarez): exclude intersections between deduced and it's cause
        self.alarms_intersects = accumulated_data.intersection

    def append_active(self, alarm_id, timestamp):

        if alarm_id in self.active_start_times:
            LOG.debug("Active alarm %s was started twice. Second time at %s",
                      alarm_id, timestamp)
            return

        self.active_start_times[alarm_id] = timestamp

    def append_inactive(self, alarm_id, end_time):

        if alarm_id not in self.active_start_times:
            LOG.debug("Alarm {} at {} was deactivated without being active".
                      format(alarm_id, str(end_time)))
            return

        alarm_duration = end_time - self.active_start_times[alarm_id]
        self.alarms_activity[alarm_id] = alarm_duration + \
            self.alarms_activity.get(alarm_id, datetime.timedelta(0))

        start_time = self.active_start_times[alarm_id]

        del self.active_start_times[alarm_id]
        self.append_intersect(alarm_id, start_time, end_time)

    def append_intersect(self, alarm_id, start_time, end_time):

        for active_alarm in self.active_start_times.items():
            key = frozenset([alarm_id, active_alarm[0]])
            active_alarm_service = active_alarm[1]
            self.alarms_intersects[key] = \
                self.alarms_intersects.get(key, datetime.timedelta(0)) + \
                self.calc_intersect(start_time, end_time, active_alarm_service)

    def calc_intersect(self, inactive_start, inactive_end, active_start):
        return inactive_end - max(inactive_start, active_start)

    def flush_accumulations(self):
        """flush all active alarms

        empty the data from active_start_times and re-enter all the
        currently-active alarms, as if they started now
        """

        now = datetime.datetime.now()
        active_alarms = list(self.active_start_times)

        for active_alarm in active_alarms:
            self.append_inactive(active_alarm, now)

        for flushed_active_alarm in active_alarms:
            self.append_active(flushed_active_alarm, now)
