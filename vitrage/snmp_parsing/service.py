# Copyright 2017 - ZTE
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

from datetime import datetime

from oslo_config import cfg
from oslo_log import log
import oslo_messaging
from oslo_utils import uuidutils
from pyasn1.codec.ber import decoder
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.carrier.asyncore.dgram import udp6
from pysnmp.carrier.asyncore.dispatch import AsyncoreDispatcher
from pysnmp.proto import api as snmp_api
from pysnmp.proto.rfc1902 import Integer
import sys

from vitrage.common.constants import EventProperties
from vitrage.coordination import service as coord
from vitrage.datasources.transformer_base import extract_field_value
from vitrage.messaging import get_transport
from vitrage.snmp_parsing.properties import SnmpEventProperties as SEProps
from vitrage.utils.file import load_yaml_file

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class SnmpParsingService(coord.Service):
    RUN_FOREVER = 1

    def __init__(self, worker_id):
        super(SnmpParsingService, self).__init__(worker_id)
        self.listening_port = CONF.snmp_parsing.snmp_listening_port
        self.oid_mapping = \
            load_yaml_file(CONF.snmp_parsing.oid_mapping)
        self._init_oslo_notifier()

    def run(self):
        super(SnmpParsingService, self).run()
        LOG.info("Vitrage SNMP Parsing Service - Starting...")

        transport_dispatcher = AsyncoreDispatcher()
        transport_dispatcher.registerRecvCbFun(self.callback_func)

        trans_udp = udp.UdpSocketTransport()
        udp_transport = \
            trans_udp.openServerMode(('0.0.0.0', self.listening_port))

        trans_udp6 = udp6.Udp6SocketTransport()
        udp6_transport = \
            trans_udp6.openServerMode(('::1', self.listening_port))

        transport_dispatcher.registerTransport(udp.domainName, udp_transport)
        transport_dispatcher.registerTransport(udp6.domainName, udp6_transport)
        LOG.info("Vitrage SNMP Parsing Service - Started!")

        transport_dispatcher.jobStarted(self.RUN_FOREVER)
        try:
            transport_dispatcher.runDispatcher()
        except Exception:
            LOG.error("Run transport dispatcher failed.")
            transport_dispatcher.closeDispatcher()
            raise

    def terminate(self):
        super(SnmpParsingService, self).terminate()
        LOG.info("Vitrage SNMP Parsing Service - Stopping...")
        LOG.info("Vitrage SNMP Parsing Service - Stopped!")

    # noinspection PyUnusedLocal
    def callback_func(self, transport_dispatcher, transport_domain,
                      transport_address, whole_msg):
        while whole_msg:
            msg_ver = int(snmp_api.decodeMessageVersion(whole_msg))
            if msg_ver in snmp_api.protoModules:
                p_mod = snmp_api.protoModules[msg_ver]
            else:
                LOG.error('Unsupported SNMP version %s.' % msg_ver)
                return
            req_msg, whole_msg = decoder.decode(
                whole_msg, asn1Spec=p_mod.Message(),
            )
            req_pdu = p_mod.apiMessage.getPDU(req_msg)
            if req_pdu.isSameTypeWith(p_mod.TrapPDU()):
                ver_binds = p_mod.apiTrapPDU.getVarBinds(req_pdu) \
                    if msg_ver == snmp_api.protoVersion1 \
                    else p_mod.apiPDU.getVarBinds(req_pdu)

                binds_dict = self._convert_binds_to_dict(ver_binds)
                LOG.debug('Receive binds info after convert: %s' % binds_dict)
                self._send_snmp_to_queue(binds_dict)

    def _convert_binds_to_dict(self, var_binds):
        binds_dict = {}
        for oid, val in var_binds:
            u_oid = self._convert_obj_to_unicode(oid)
            binds_dict[u_oid] = int(val) if isinstance(val, Integer) \
                else self._convert_obj_to_unicode(val)
        return binds_dict

    @staticmethod
    def _convert_obj_to_unicode(val):
        if sys.version_info[0] < 3:
            return str(val).decode('iso-8859-1')
        return str(val)

    def _init_oslo_notifier(self):
        self.oslo_notifier = None
        try:
            self.publisher = 'vitrage-snmp-parsing'
            self.oslo_notifier = oslo_messaging.Notifier(
                get_transport(),
                driver='messagingv2',
                publisher_id=self.publisher,
                topics=['vitrage_notifications'])
        except Exception:
            LOG.exception('Failed to initialize oslo notifier')

    def _send_snmp_to_queue(self, snmp_trap):
        try:
            event_type = self._get_event_type(snmp_trap)
            if not event_type:
                return
            event = {EventProperties.TIME: datetime.utcnow(),
                     EventProperties.TYPE: event_type,
                     EventProperties.DETAILS: snmp_trap}
            LOG.debug('snmp oslo_notifier event: %s' % event)
            self.oslo_notifier.info(
                ctxt={'message_id': uuidutils.generate_uuid(),
                      'publisher_id': self.publisher,
                      'timestamp': datetime.utcnow()},
                event_type=event_type,
                payload=event)
        except Exception as e:
            LOG.warning('Snmp failed to post event. Exception: %s', e)

    def _get_event_type(self, snmp_trap):
        if not self.oid_mapping:
            LOG.warning('No snmp trap is configured!')
            return None

        for mapping_info in self.oid_mapping:
            system_oid = extract_field_value(mapping_info, SEProps.SYSTEM_OID)
            conf_system = extract_field_value(mapping_info, SEProps.SYSTEM)
            if conf_system == extract_field_value(snmp_trap, system_oid):
                LOG.debug('snmp trap mapped the system: %s.' % conf_system)
                return extract_field_value(mapping_info, SEProps.EVENT_TYPE)

        LOG.error("Snmp trap does not contain system info!")
        return None
