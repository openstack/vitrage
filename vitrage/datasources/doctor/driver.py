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

from collections import namedtuple
from oslo_log import log

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EventProperties as EventProps
from vitrage.datasources.alarm_driver_base import AlarmDriverBase
from vitrage.datasources.doctor import DOCTOR_DATASOURCE
from vitrage.datasources.doctor.properties import DoctorDetails
from vitrage.datasources.doctor.properties import DoctorProperties \
    as DoctorProps
from vitrage.datasources.doctor.properties import DoctorStatus
from vitrage.datasources.doctor.properties import get_detail

LOG = log.getLogger(__name__)


class DoctorDriver(AlarmDriverBase):
    AlarmKey = namedtuple('AlarmKey', ['alarm_name', 'hostname'])

    def __init__(self):
        super(DoctorDriver, self).__init__()
        self._client = None

    def _vitrage_type(self):
        return DOCTOR_DATASOURCE

    def _alarm_key(self, alarm):
        return self.AlarmKey(alarm_name=alarm[EventProps.TYPE],
                             hostname=get_detail(alarm,
                                                 DoctorDetails.HOSTNAME))

    def _is_erroneous(self, alarm):
        return alarm and \
            get_detail(alarm, DoctorDetails.STATUS) != DoctorStatus.UP

    def _is_valid(self, alarm):
        if not alarm or EventProps.TIME not in alarm or \
                EventProps.TYPE not in alarm or \
                EventProps.DETAILS not in alarm:
            return False

        details = alarm[EventProps.DETAILS]
        return DoctorDetails.STATUS in details and \
            DoctorDetails.HOSTNAME in details

    def _status_changed(self, new_alarm, old_alarm):
        return get_detail(old_alarm, DoctorDetails.STATUS) != \
            get_detail(new_alarm, DoctorDetails.STATUS)

    def get_all(self, datasource_action):
        # pulling alarms is not supported in Doctor monitor
        return self.make_pickleable([], DOCTOR_DATASOURCE, datasource_action)

    def get_changes(self, datasource_action):
        # pulling alarms is not supported in Doctor monitor
        return self.make_pickleable([], DOCTOR_DATASOURCE, datasource_action)

    def enrich_event(self, event, event_type):
        """Enrich the given event

        :param event: dictionary of this form:
            {
                'time': '2016-04-12T08:00:00.12345',
                'type': 'compute.host.down',
                'details': {
                    'hostname': 'compute-1',
                    'source': 'sample_monitor',
                    'cause': 'link-down',
                    'severity': 'critical',
                    'status': 'down',
                    'monitor_id': 'monitor-1',
                    'monitor_event_id': '123',
                }
            }
        :param event_type: always 'compute.host.down'
        :return: the same event, with the following changes:
            - DoctorProps.UPDATE_TIME - the event 'time' if it is new, or the
                update time of the same event if it is already cached

        """

        LOG.debug('Going to enrich event: %s', event)

        event[DSProps.EVENT_TYPE] = event[EventProps.TYPE]

        old_alarm = self._old_alarm(event)
        if old_alarm and not self._status_changed(old_alarm, event):
            event[DoctorProps.UPDATE_TIME] = old_alarm[DoctorProps.UPDATE_TIME]
        else:
            event[DoctorProps.UPDATE_TIME] = event[EventProps.TIME]

        event = self._filter_and_cache_alarm(event, old_alarm,
                                             self._filter_get_erroneous,
                                             event[EventProps.TIME])

        LOG.debug('Enriched event: %s', event)

        if event:
            return DoctorDriver.make_pickleable([event], DOCTOR_DATASOURCE,
                                                DatasourceAction.UPDATE)[0]

    @staticmethod
    def get_event_types():
        return [DoctorProps.CUSTOM_EVENT_DOWN,
                DoctorProps.CUSTOM_EVENT_UP]
