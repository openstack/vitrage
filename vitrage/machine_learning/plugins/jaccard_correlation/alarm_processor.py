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

from collections import namedtuple
from datetime import datetime

from oslo_config import cfg
from oslo_log import log

from vitrage.common.constants import NotifierEventTypes
from vitrage.common.constants import VertexProperties as VProps
from vitrage.datasources.alarm_properties import AlarmProperties as AlarmProps
from vitrage.datasources.transformer_base import TIMESTAMP_FORMAT
from vitrage.machine_learning.plugins.base import MachineLearningBase
import vitrage.machine_learning.plugins.jaccard_correlation.\
    accumulation_persistor_utils as APersistor
from vitrage.machine_learning.plugins.jaccard_correlation.\
    alarm_data_accumulator import AlarmDataAccumulator as ADAcummulator
from vitrage.machine_learning.plugins.jaccard_correlation.correlation_manager\
    import CorrelationManager as CM

CONF = cfg.CONF

LOG = log.getLogger(__name__)

AlarmID = namedtuple('AlarmID', [VProps.VITRAGE_RESOURCE_ID,
                                 VProps.VITRAGE_RESOURCE_TYPE,
                                 VProps.NAME])


class AlarmDataProcessor(MachineLearningBase):

    @staticmethod
    def get_plugin_name():
        return 'jaccard_correlation'

    def __init__(self):
        super(AlarmDataProcessor, self).__init__()
        self.data_manager = ADAcummulator(APersistor.load_data())
        self.correlation_manager = CM()
        self.num_of_events_to_flush = \
            CONF.jaccard_correlation.num_of_events_to_flush
        self.event_counter = 0

    def process_event(self, data, event_type):

        if event_type == NotifierEventTypes.ACTIVATE_ALARM_EVENT \
                or event_type == NotifierEventTypes.DEACTIVATE_ALARM_EVENT:

            # TODO(annarez): handle alarms from collectd
            if data[VProps.VITRAGE_TYPE] == 'collectd':
                return

            self._update_data_accumulator(data)
            self.event_counter += 1

            # flush all data once num_of_events_to_flush is achieved
            if self.event_counter == self.num_of_events_to_flush:
                LOG.debug("Persisting: %s", data)
                self.data_manager.flush_accumulations()
                APersistor.save_accumulated_data(self.data_manager)
                self.correlation_manager.output_correlations(self.data_manager)
                self.event_counter = 0

    def _update_data_accumulator(self, data):

        alarm_name = data[VProps.RAWTEXT] if data.get(VProps.RAWTEXT) else \
            data[VProps.NAME]

        alarm_id, timestamp = \
            self._get_alarm_id_and_timestamp(data, alarm_name)

        if data[VProps.STATE] == AlarmProps.ACTIVE_STATE:
            self.data_manager.append_active(alarm_id, timestamp)
        else:
            self.data_manager.append_inactive(alarm_id, timestamp)

    @staticmethod
    def _get_alarm_id_and_timestamp(data, alarm_name):

        alarm_id = AlarmID(data.get(VProps.VITRAGE_RESOURCE_ID),
                           data.get(VProps.VITRAGE_RESOURCE_TYPE),
                           alarm_name)

        timestamp = datetime.strptime(data[VProps.UPDATE_TIMESTAMP],
                                      TIMESTAMP_FORMAT)

        return alarm_id, timestamp
