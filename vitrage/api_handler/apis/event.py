# Copyright 2017 - Nokia Corporation
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

from datetime import datetime
from oslo_log import log
import oslo_messaging
from oslo_utils import uuidutils
from osprofiler import profiler
import socket

from vitrage.common.constants import EventProperties
from vitrage.datasources.doctor.properties import DoctorDetails
from vitrage.datasources.doctor.properties import DoctorProperties
from vitrage.datasources.doctor.properties import DoctorStatus
from vitrage.messaging import get_transport

LOG = log.getLogger(__name__)


@profiler.trace_cls("event apis",
                    info={}, hide_args=False, trace_private=False)
class EventApis(object):

    def __init__(self):
        self._init_oslo_notifier()

    def post(self, ctx, event_time, event_type, details):
        try:
            event = {EventProperties.TYPE: event_type,
                     EventProperties.TIME: event_time,
                     EventProperties.DETAILS: details}
            if details.get(DoctorDetails.STATUS) == DoctorStatus.UP:
                notification_type = DoctorProperties.CUSTOM_EVENT_UP
            elif details.get(DoctorDetails.STATUS) == DoctorStatus.DOWN:
                notification_type = DoctorProperties.CUSTOM_EVENT_DOWN
            else:
                notification_type = event_type

            self.oslo_notifier.info(
                ctxt={'message_id': uuidutils.generate_uuid(),
                      'publisher_id': self.publisher,
                      'timestamp': datetime.utcnow()},
                event_type=notification_type,
                payload=event)
        except Exception as e:
            LOG.warning('Failed to post event %s. Exception: %s',
                        event_type, e)
            LOG.debug(e, exc_info=True)

    def _init_oslo_notifier(self):
        self.oslo_notifier = None
        try:
            self.publisher = 'api_%s' % socket.gethostname()

            self.oslo_notifier = oslo_messaging.Notifier(
                get_transport(),
                driver='messagingv2',
                publisher_id=self.publisher,
                topics=['vitrage_notifications'])
        except Exception:
            LOG.exception('Failed to initialize oslo notifier')
