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

import os
import time

from oslo_config import cfg
from oslo_log import log

from vitrage.machine_learning.plugins.jaccard_correlation.\
    correlation_collection import CorrelationCollection as CCollection
from vitrage.machine_learning.plugins.jaccard_correlation.\
    correlation_collection import CorrelationPriorities as CPriorities


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class CorrelationManager(object):

    def __init__(self):
        self.high_corr_score = CONF.jaccard_correlation.high_corr_score
        self.med_corr_score = CONF.jaccard_correlation.med_corr_score
        self.correlation_threshold = \
            CONF.jaccard_correlation.correlation_threshold
        self.output_folder = CONF.jaccard_correlation.output_folder
        self.last_written_file = ""
        self.correlation_table = CCollection(self.high_corr_score,
                                             self.med_corr_score)

    def output_correlations(self, accumulated_data):
        now = int(time.time())
        report = self._generate_report(accumulated_data)

        self._dump_correlations(str(now) + "_correlations.out", dict(report))

    @staticmethod
    def _jaccard_score(alarm_1, alarm_2, accumulated_data):
        key = frozenset([alarm_1, alarm_2])
        intersect = accumulated_data.alarms_intersects.get(key)

        if not intersect:
            return 0

        a1_time = accumulated_data.alarms_activity.get(alarm_1)
        a2_time = accumulated_data.alarms_activity.get(alarm_2)
        if not a1_time or not a2_time:
            LOG.error("One of the alarms given has never been active")
            return 0

        combined = a1_time + a2_time - intersect
        # jaccard is intersection / union of alarm times
        return intersect.total_seconds() / combined.total_seconds()

    def _generate_report(self, accumulated_data):

        for alarm_1, alarm_2 in accumulated_data.alarms_intersects.keys():

            jacc_score = \
                self._jaccard_score(alarm_1, alarm_2, accumulated_data)

            if jacc_score >= self.correlation_threshold:
                self.correlation_table.set(alarm_1, alarm_2, 0, jacc_score)

        # mean correlations divided to HIGH, MEDIUM and LOW correlation scores
        report = self.correlation_table.get_aggregated()
        return report

    def _dump_correlations(self, output_path, alarms):

        new_file_name = "{}/{}".format(self.output_folder, output_path)

        try:
            with open(new_file_name, 'w') as f:
                LOG.info("Correlation manager wrote a new file: {}/{}".format
                         (self.output_folder, output_path))

                for correlation_level, correlation_bar \
                        in [(CPriorities.HIGH,
                             " (> {})".format(self.high_corr_score)),
                            (CPriorities.MEDIUM,
                             " (> {})".format(self.med_corr_score)),
                            (CPriorities.LOW,
                             "(< {})".format(self.med_corr_score))]:
                    if correlation_level in alarms:

                        title = correlation_level + \
                            " correlation" + correlation_bar + ":"

                        f.write("\n" + title + "\n" +
                                ("-" * len(title)) + "\n")

                        for alarm in alarms[correlation_level]:
                            f.write("alarm " + alarm[0][1] + " on " +
                                    alarm[0][0] + " <-> alarm " +
                                    alarm[0][3] + " on " + alarm[0][2] +
                                    " with score " + str(alarm[1]) + "\n")
        except Exception:
            LOG.exception('Cannot save correlations.')

        if os.path.isfile(self.last_written_file):
            os.remove(self.last_written_file)

        self.last_written_file = new_file_name
