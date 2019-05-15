# Copyright 2017 - Nokia
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

import datetime
import os.path
from oslo_config import cfg
import time

from testtools import matchers

from vitrage.common.constants import EntityCategory
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.aodh import AODH_DATASOURCE
from vitrage.datasources.transformer_base import TIMESTAMP_FORMAT
from vitrage.datasources.zabbix import ZABBIX_DATASOURCE
from vitrage.evaluator.actions import evaluator_event_transformer as evaluator
from vitrage.graph import Vertex
from vitrage.machine_learning.plugins.jaccard_correlation.\
    accumulation_persistor_utils import AccumulatedData as AData
from vitrage.machine_learning.plugins.jaccard_correlation.\
    alarm_data_accumulator import AlarmDataAccumulator as ADAccumulator
from vitrage.machine_learning.plugins.jaccard_correlation.\
    alarm_processor import AlarmDataProcessor as ADProcessor
from vitrage.machine_learning.plugins.jaccard_correlation.\
    alarm_processor import AlarmID
from vitrage.machine_learning.plugins.jaccard_correlation.\
    correlation_collection import CorrelationCollection as CCollection
from vitrage.machine_learning.plugins.jaccard_correlation.correlation_manager \
    import CorrelationManager as CManager
from vitrage.machine_learning.plugins.jaccard_correlation.\
    correlation_collection import CorrelationPriorities as CPriorities
from vitrage.tests import base

CONF = cfg.CONF

ACTIVE_TIMESTAMP = datetime.datetime.utcnow()
ACTIVE_TIMESTAMP = ACTIVE_TIMESTAMP.strftime(TIMESTAMP_FORMAT)
INACTIVE_TIMESTAMP = \
    datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
INACTIVE_TIMESTAMP = INACTIVE_TIMESTAMP.strftime(TIMESTAMP_FORMAT)

DEDUCED_ALARM_1 = Vertex('111', {
    VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
    VProps.VITRAGE_TYPE: evaluator.VITRAGE_DATASOURCE,
    VProps.VITRAGE_IS_DELETED: False,
    VProps.VITRAGE_IS_PLACEHOLDER: False,
    VProps.NAME: 'deduced_alarm_1',
    VProps.UPDATE_TIMESTAMP: ACTIVE_TIMESTAMP,
    VProps.VITRAGE_RESOURCE_ID: '111',
    VProps.VITRAGE_RESOURCE_TYPE: 'resource_111',
    })

AODH_ALARM_1 = Vertex('11', {
    VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
    VProps.VITRAGE_TYPE: AODH_DATASOURCE,
    VProps.VITRAGE_IS_DELETED: False,
    VProps.VITRAGE_IS_PLACEHOLDER: False,
    VProps.NAME: 'aodh_alarm_1',
    VProps.UPDATE_TIMESTAMP: ACTIVE_TIMESTAMP,
    VProps.VITRAGE_RESOURCE_ID: '11',
    VProps.VITRAGE_RESOURCE_TYPE: 'resource_11',
    })

ZABBIX_ALARM_1 = Vertex('1111', {
    VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
    VProps.VITRAGE_TYPE: ZABBIX_DATASOURCE,
    VProps.VITRAGE_IS_DELETED: False,
    VProps.VITRAGE_IS_PLACEHOLDER: True,
    VProps.NAME: 'zabbix_alarm_1 {}',
    VProps.RAWTEXT: 'zabbix_alarm_1',
    VProps.UPDATE_TIMESTAMP: ACTIVE_TIMESTAMP,
    VProps.VITRAGE_RESOURCE_ID: '1111',
    VProps.VITRAGE_RESOURCE_TYPE: 'resource_1111',
    })

ZABBIX_ALARM_2 = Vertex('2222', {
    VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
    VProps.VITRAGE_TYPE: ZABBIX_DATASOURCE,
    VProps.VITRAGE_IS_DELETED: False,
    VProps.VITRAGE_IS_PLACEHOLDER: True,
    VProps.NAME: 'zabbix_alarm_2 {}',
    VProps.RAWTEXT: 'zabbix_alarm_2',
    VProps.UPDATE_TIMESTAMP: ACTIVE_TIMESTAMP,
    VProps.VITRAGE_RESOURCE_ID: '2222',
    VProps.VITRAGE_RESOURCE_TYPE: 'resource_2222',
})

DELETED_DEDUCED_ALARM_1 = Vertex('111', {
    VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
    VProps.VITRAGE_TYPE: evaluator.VITRAGE_DATASOURCE,
    VProps.VITRAGE_IS_DELETED: True,
    VProps.VITRAGE_IS_PLACEHOLDER: False,
    VProps.NAME: 'deduced_alarm_1',
    VProps.UPDATE_TIMESTAMP: INACTIVE_TIMESTAMP,
    VProps.VITRAGE_RESOURCE_ID: '111',
    VProps.VITRAGE_RESOURCE_TYPE: 'resource_111',
})

DELETED_AODH_ALARM_1 = Vertex('11', {
    VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
    VProps.VITRAGE_TYPE: evaluator.VITRAGE_DATASOURCE,
    VProps.VITRAGE_IS_DELETED: True,
    VProps.VITRAGE_IS_PLACEHOLDER: False,
    VProps.NAME: 'aodh_alarm_1',
    VProps.UPDATE_TIMESTAMP: INACTIVE_TIMESTAMP,
    VProps.VITRAGE_RESOURCE_ID: '11',
    VProps.VITRAGE_RESOURCE_TYPE: 'resource_11',
})

DELETED_ZABBIX_ALARM_1 = Vertex('1111', {
    VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
    VProps.VITRAGE_TYPE: ZABBIX_DATASOURCE,
    VProps.VITRAGE_IS_DELETED: True,
    VProps.VITRAGE_IS_PLACEHOLDER: False,
    VProps.NAME: 'zabbix_alarm_1 {}',
    VProps.RAWTEXT: 'zabbix_alarm_1',
    VProps.UPDATE_TIMESTAMP: INACTIVE_TIMESTAMP,
    VProps.VITRAGE_RESOURCE_ID: '1111',
    VProps.VITRAGE_RESOURCE_TYPE: 'resource_1111',
})

DELETED_ZABBIX_ALARM_2 = Vertex('2222', {
    VProps.VITRAGE_CATEGORY: EntityCategory.ALARM,
    VProps.VITRAGE_TYPE: ZABBIX_DATASOURCE,
    VProps.VITRAGE_IS_DELETED: True,
    VProps.VITRAGE_IS_PLACEHOLDER: False,
    VProps.NAME: 'zabbix_alarm_2 {}',
    VProps.RAWTEXT: 'zabbix_alarm_2',
    VProps.UPDATE_TIMESTAMP: INACTIVE_TIMESTAMP,
    VProps.VITRAGE_RESOURCE_ID: '2222',
    VProps.VITRAGE_RESOURCE_TYPE: 'resource_2222',
})

ACTIVE_ALARMS = [DEDUCED_ALARM_1, AODH_ALARM_1,
                 ZABBIX_ALARM_1, ZABBIX_ALARM_2]

INACTIVE_ALARMS = [DELETED_DEDUCED_ALARM_1, DELETED_AODH_ALARM_1,
                   DELETED_ZABBIX_ALARM_1, DELETED_ZABBIX_ALARM_2]


class JaccardCorrelationTest(base.BaseTest):
    def setUp(self):
        super(JaccardCorrelationTest, self).setUp()

        self.data_manager = ADAccumulator(AData({}, {}))
        self.collection = \
            CCollection(CONF.jaccard_correlation.high_corr_score,
                        CONF.jaccard_correlation.med_corr_score)
        self.correlation_manager = CManager()
        self.activate_timestamps = {}
        self.inactivate_timestamps = {}
        self.alarm_ids = self._setup_expected_active_alarms_ids()

    def _setup_expected_active_alarms_ids(self):
        alarm_ids = []
        for alarm in ACTIVE_ALARMS:
            alarm_name = alarm[VProps.RAWTEXT] if alarm.get(VProps.RAWTEXT) \
                else alarm[VProps.NAME]
            alarm_id = AlarmID(alarm.get(VProps.VITRAGE_RESOURCE_ID),
                               alarm.get(VProps.VITRAGE_RESOURCE_TYPE),
                               alarm_name)
            alarm_ids.append(alarm_id)

        return alarm_ids

    def test_jaccard_correlation(self):
        self._test_alarm_data_accumulations()
        self._test_correlation_collection()
        self._test_correlation_manager()

    def _test_alarm_data_accumulations(self):
        self._test_append_active()
        self._test_flush_accumulations()
        self._test_append_inactive()

    def _test_append_active(self):

        expected_active_start_dict = {}
        real_alarm_ids = []

        for alarm in ACTIVE_ALARMS:

            alarm_name = alarm[VProps.RAWTEXT] if alarm.get(VProps.RAWTEXT) \
                else alarm[VProps.NAME]

            alarm_id, timestamp = ADProcessor.\
                _get_alarm_id_and_timestamp(alarm, alarm_name)

            self.activate_timestamps[alarm_id] = timestamp
            expected_active_start_dict[alarm_id] = \
                datetime.datetime.strptime(alarm.get(VProps.UPDATE_TIMESTAMP),
                                           TIMESTAMP_FORMAT)

            real_alarm_ids.append(alarm_id)
            self.data_manager.append_active(alarm_id, timestamp)

        # assert all alarm ids are right
        self.assert_list_equal(self.alarm_ids, real_alarm_ids)

        self.assert_dict_equal(expected_active_start_dict,
                               self.data_manager.active_start_times)

        self.assert_is_empty(self.data_manager.alarms_activity)
        self.assert_is_empty(self.data_manager.alarms_intersects)

    def _test_flush_accumulations(self):

        prev_active_start_dict = self.data_manager.active_start_times

        time.sleep(2)
        self.data_manager.flush_accumulations()

        self.assert_dict_equal(prev_active_start_dict,
                               self.data_manager.active_start_times)

        expected_activity_dict_len = len(ACTIVE_ALARMS)
        self.assertThat(self.data_manager.alarms_activity,
                        matchers.HasLength(expected_activity_dict_len))

        # choose 2
        expected_intersections_dict_len = \
            (len(ACTIVE_ALARMS) * (len(ACTIVE_ALARMS) - 1)) / 2
        self.assertThat(self.data_manager.alarms_intersects,
                        matchers.HasLength(expected_intersections_dict_len))

    def _test_append_inactive(self):
        deleted_alarm_ids = []

        for alarm in INACTIVE_ALARMS:
            alarm_name = alarm[VProps.RAWTEXT] if alarm.get(VProps.RAWTEXT) \
                else alarm[VProps.NAME]

            alarm_id, timestamp = ADProcessor.\
                _get_alarm_id_and_timestamp(alarm, alarm_name)

            expected_alarm_id = \
                AlarmID(alarm.get(VProps.VITRAGE_RESOURCE_ID),
                        alarm.get(VProps.VITRAGE_RESOURCE_TYPE),
                        alarm_name)

            self.assertEqual(expected_alarm_id, alarm_id)

            self.inactivate_timestamps[alarm_id] = timestamp
            deleted_alarm_ids.append(alarm_id)

            self.data_manager.append_inactive(alarm_id, timestamp)

        # assert all deleted alarms has same alarm ids as activated alarms
        self.assert_list_equal(self.alarm_ids, deleted_alarm_ids)

        # all alarm are inactive at this moment
        expected_active_start_dict = {}
        self.assert_dict_equal(expected_active_start_dict,
                               self.data_manager.active_start_times)

        expected_activity_dict = {}

        for alarm_id in self.alarm_ids:
            expected_activity_dict[alarm_id] = \
                self.inactivate_timestamps[alarm_id]\
                - self.activate_timestamps[alarm_id]

        self.assert_dict_equal(expected_activity_dict,
                               self.data_manager.alarms_activity)

        expected_intersections_dict = {}

        # all alarms started and ended at the same time,
        # intersection time equals activity time
        for alarm_id1 in self.alarm_ids:
            for alarm_id2 in self.alarm_ids:
                # exclude intersection of alarm with itself
                if alarm_id1 != alarm_id2:
                    key = frozenset([alarm_id1, alarm_id2])
                    expected_intersections_dict[key] = \
                        self.inactivate_timestamps[alarm_id]\
                        - self.activate_timestamps[alarm_id]

        self.assert_dict_equal(expected_intersections_dict,
                               self.data_manager.alarms_intersects)

    def _test_correlation_collection(self):
        self._test_correlation_list()
        self._test_correlations_aggregation()
        self.collection = CCollection(0.9, 0.5)

    def _test_correlation_list(self):
        offset_delta = 0
        high_correlation = 0.9
        med_correlation = 0.7
        low_correlation = 0.4

        correlations = [high_correlation, med_correlation, low_correlation]
        alarms_pairs = []
        cnt = 0

        seen_pairs = []

        for alarm1 in self.alarm_ids:
            for alarm2 in self.alarm_ids:
                if alarm1 != alarm2 \
                        and frozenset([alarm1, alarm2]) not in seen_pairs:
                    seen_pairs.append(frozenset([alarm1, alarm2]))
                    correlation = correlations[cnt % 3]
                    alarms_pairs.append((alarm1 + alarm2 +
                                         (offset_delta, correlation)))

                    self.collection.set(alarm1, alarm2, offset_delta,
                                        correlation)
                    cnt += 1

        self.assert_list_equal(alarms_pairs, self.collection.correlation_list)

    def _test_correlations_aggregation(self):

        aggregated = self.collection.get_aggregated()
        cnt_high_correlations = 0
        cnt_med_correlations = 0
        cnt_low_correlations = 0

        for correlation_level in aggregated:
            if correlation_level[0] == CPriorities.HIGH:
                cnt_high_correlations = len(correlation_level[1])
            if correlation_level[0] == CPriorities.MEDIUM:
                cnt_med_correlations = len(correlation_level[1])
            if correlation_level[0] == CPriorities.LOW:
                cnt_low_correlations = len(correlation_level[1])

        self.assertEqual(cnt_high_correlations, 2)
        self.assertEqual(cnt_med_correlations, 2)
        self.assertEqual(cnt_low_correlations, 2)

    def _test_correlation_manager(self):
        report = []
        self._test_generate_report(report)
        self._test_dump_correlations(report)

    def _test_generate_report(self, report):
        self.data_manager.flush_accumulations()
        report.extend(self.correlation_manager.
                      _generate_report(self.data_manager))

        # all intersects correlations are 1
        self.assertEqual(CPriorities.HIGH, report[0][0])
        self.assertEqual(len(self.data_manager.alarms_intersects),
                         len(report[0][1]))

    def _test_dump_correlations(self, report):
        now = int(time.time())

        self.correlation_manager.\
            _dump_correlations(str(now) + "_correlations_test.out",
                               report)

        file_path = CONF.jaccard_correlation.output_folder + '/' + \
            str(now) + "_correlations_test.out"
        is_file = os.path.isfile(file_path)

        self.assertTrue(is_file)

        if os.path.isfile(file_path):
            os.remove(file_path)
