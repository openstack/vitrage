# Copyright 2016 - Nokia
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
from oslo_log import log
import oslo_messaging as oslo_msg


CONF = cfg.CONF
LOG = log.getLogger(__name__)

DEFAULT_URL = "__default__"
TRANSPORTS = {}
# _SERIALIZER = oslo_serializer.JsonPayloadSerializer()


def setup():
    # Set the default exchange under which topics are scoped
    oslo_msg.set_transport_defaults('vitrage')


def get_rpc_transport(url=None, optional=False, cache=True):
    return get_transport(url, optional, cache, rpc=True)


def get_transport(url=None, optional=False, cache=True, rpc=False):
    """Initialise the oslo_messaging layer."""
    global TRANSPORTS, DEFAULT_URL
    cache_key = url or DEFAULT_URL + '_rpc' if rpc else ''
    transport = TRANSPORTS.get(cache_key)
    if not transport or not cache:
        try:
            if rpc:
                transport = oslo_msg.get_rpc_transport(CONF, url)
            else:
                transport = oslo_msg.get_notification_transport(CONF, url)
        except oslo_msg.InvalidTransportURL as e:
            if not optional or e.url:
                # NOTE(sileht): oslo_messaging is configured but unloadable
                # so reraise the exception
                raise
            return None
        else:
            if cache:
                TRANSPORTS[cache_key] = transport
    return transport


def get_notification_listener(transport, targets, endpoints,
                              allow_requeue=False):
    """Return a configured oslo_messaging notification listener."""
    return oslo_msg.get_notification_listener(
        transport, targets, endpoints, allow_requeue=allow_requeue)


class VitrageNotifier(object):
    """Allows writing to message bus"""
    def __init__(self, publisher_id, topics):
        transport = get_transport()
        self.notifier = oslo_msg.Notifier(
            transport,
            driver='messagingv2',
            publisher_id=publisher_id,
            topics=topics)

    def notify(self, event_type, data):
        LOG.debug('notify : ' + event_type + ' ' + str(data))
        if self.notifier:
            try:
                self.notifier.info({}, event_type, data)
            except Exception:
                LOG.exception('Notifier cannot notify.')
        else:
            LOG.error('Notifier cannot notify')
