# Copyright 2017 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from vitrage.common.constants import NotifierEventTypes
from vitrage.common.constants import VertexProperties as VProps
from vitrage.notifier.plugins.base import NotifierBase

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class SnmpNotifier(NotifierBase):
    @staticmethod
    def get_notifier_name():
        return 'snmp'

    def __init__(self):
        super(SnmpNotifier, self).__init__()
        self.snmp_sender = \
            importutils.import_object(CONF.snmp.snmp_sender_class)

    def process_event(self, data, event_type):

        if event_type == NotifierEventTypes.ACTIVATE_DEDUCED_ALARM_EVENT \
                or event_type == \
                NotifierEventTypes.DEACTIVATE_DEDUCED_ALARM_EVENT:

            LOG.info('Vitrage snmp Info: Sending snmp trap')

            try:
                self.snmp_sender.send_snmp(self._parse_alarm_data(data))
            except Exception:
                LOG.exception('Vitrage SNMP Error: Failed to send SNMP trap.')

    @staticmethod
    def _parse_alarm_data(data):

        new_data_format = {}

        for key, val in data.items():
            # TODO(ifat_afek): quick and dirty bug fix for Queens for
            # https://bugs.launchpad.net/vitrage/+bug/1747895
            #
            # RESOURCE_ID is automatically generated with the correct value by
            # "RESOURCE_ + ID" in the loop below.
            # The problem is that for deduced alarms there is also a
            # RESOURCE_ID property in the data that holds the vitrage_id of the
            # resource instead of its id.
            # In some cases it overwrites the right auto-generated RESOURCE_ID.
            # The RESOURCE_ID should probably be deleted from deduced alarms,
            # but for now we just ignore it in the SNMP notifier.
            if key != VProps.RESOURCE_ID:
                new_data_format[key] = val

            if key == VProps.RESOURCE:
                # For each property of the resource, generate a RESOURCE_+key
                # property in the alarm
                for k, v in val.items():
                    new_data_format[VProps.RESOURCE + '_' + str(k)] = v

        return new_data_format
