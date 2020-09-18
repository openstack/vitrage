# -*- coding: utf-8 -*-
#
# © 2016 Nokia Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.  You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Collectd plugin for sending notifications to vitrage
"""

import collectd
import hashlib
from vitrage.datasources.collectd import COLLECTD_DATASOURCE

from vitrage.datasources.collectd.collectd_vitrage.plugin import CollectDPlugin
from vitrage.datasources.collectd.collectd_vitrage.plugin import PluginError


from datetime import datetime
from oslo_config import cfg
from oslo_utils import uuidutils

import oslo_messaging as messaging


class VitrageNotifier(CollectDPlugin):
    """Collectd plugin for sending notifications to Vitrage. """

    def configure(self, config, **kwargs):

        super(VitrageNotifier, self).configure(config, **kwargs)

        # to be filled later
        for key in ('transport_url',):
            if key not in self.config.keys():
                message = 'Required configuration key %s missing!' % key
                self.error(message)
                raise PluginError(message)

    def initialize(self):
        """Set up the Vitrage API client and add the notification callback. """

        url = self.config['transport_url']
        transport = messaging.get_notification_transport(cfg.CONF, url)
        self.notifier = messaging.Notifier(transport,
                                           driver='messagingv2',
                                           publisher_id=COLLECTD_DATASOURCE,
                                           topics=['vitrage_notifications'])
        self.add_notification_callback(self.notify)

    def notify(self, notification):
        """Send the notification to Vitrage. """

        # Use a friendly string instead of a number.
        severity = {
            collectd.NOTIF_FAILURE: 'FAILURE',
            collectd.NOTIF_WARNING: 'WARNING',
            collectd.NOTIF_OKAY: 'OK',
        }.get(notification.severity)

        alarm_uuid = self._generate_alarm_id(notification)
        payload = self._create_payload(alarm_uuid, notification, severity)
        notification_id = uuidutils.generate_uuid()

        self.notifier.info(ctxt={'message_id': notification_id,
                                 'publisher_id': COLLECTD_DATASOURCE,
                                 'timestamp': datetime.utcnow()},
                           event_type='collectd.alarm.' + severity.lower(),
                           payload=payload)

        self.info('notification id %r to vitrage: %r' % (notification_id,
                                                         payload))

    @staticmethod
    def _create_payload(alarm_uuid, notification, severity):
        payload = {
            'host': notification.host,
            'plugin': notification.plugin,
            'collectd_type': notification.type,
            'message': notification.message,
            'severity': severity,
            'time': notification.time,
            'id': alarm_uuid
        }
        if notification.plugin_instance:
            payload['plugin_instance'] = notification.plugin_instance
        if notification.type_instance:
            payload['type_instance'] = notification.type_instance
        return payload

    @staticmethod
    def _generate_alarm_id(notification):
        resources = [notification.host, notification.plugin_instance,
                     notification.type_instance, notification.type]
        alarm_id = ''.join([resource for resource in resources if resource])
        alarm_uuid = hashlib.md5(alarm_id.encode("latin-1")).hexdigest()
        return alarm_uuid


# We have to call the constructor in order to actually register our plugin
# with collectd.
VITRAGE = VitrageNotifier()
