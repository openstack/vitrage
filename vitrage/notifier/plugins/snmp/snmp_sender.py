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
from pysnmp.entity.engine import SnmpEngine
from pysnmp.hlapi.asyncore.sync.compat.ntforg import sendNotification
from pysnmp.hlapi.asyncore.transport import UdpTransportTarget
from pysnmp.hlapi.auth import CommunityData
from pysnmp.hlapi.context import ContextData
from pysnmp.proto.rfc1902 import OctetString
from pysnmp.smi.rfc1902 import NotificationType
from pysnmp.smi.rfc1902 import ObjectIdentity
import re

from vitrage.common.constants import VertexProperties as VProps
from vitrage.notifier.plugins.snmp.base import SnmpSenderBase
from vitrage.utils.file import load_yaml_file

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

# TODO(annarez): change NA to N/A
NA = 'NA'
SNMP_TREE = 'snmp_tree'
SEVERITY_MAPPING = 'severity_mapping'
OID = 'oid'
NEXT = 'next'
WITH_VALS = 'with_values'
SEVERITY = 'SEVERITY'
ALARM_OID = 'ALARM_OID'
IP_PAT = re.compile(r'\d+\.\d+\.\d+\.\d+')
PORT_PAT = re.compile(r'\d+')


class SnmpSender(SnmpSenderBase):
    def __init__(self):
        self.hosts = load_yaml_file(CONF.snmp.consumers, True)
        self.oid_tree = load_yaml_file(CONF.snmp.oid_tree, True)
        self.alarm_mapping = \
            load_yaml_file(CONF.snmp.alarm_oid_mapping, True)
        self.oids, self.var_fields = self._build_oids()

    def send_snmp(self, alarm_data):

        alert_details, alert_severity_oid = self._get_details(alarm_data)

        if alert_details:
            alarm_oid = \
                self._get_alert_oid(alert_details[OID], alert_severity_oid)
            if not alarm_oid:
                return
            for host in self.hosts:
                self._send_snmp_trap(host,
                                     self._get_var_binds(alarm_data),
                                     alarm_oid)
        else:
            LOG.info('Vitrage snmp Info: Unrecognized alarm. Alarm type: %s',
                     alarm_data[VProps.NAME])

    def _get_details(self, alarm_data):

        if not (self.hosts and self.alarm_mapping and
                self.oids and self.var_fields):
            LOG.error('Vitrage snmp Error: definitions is '
                      'missing from configuration file')
            return None, None

        alert_severity_oid = self._get_severity_oid(alarm_data)

        if not alert_severity_oid and \
                self.oids.get(SEVERITY):
            LOG.error('Vitrage snmp Error: there '
                      'is no severity mapping in file')
            return None, None

        alarm_name = alarm_data.get(VProps.NAME)
        alert_details = self.alarm_mapping.get(alarm_name)

        return alert_details, alert_severity_oid

    def _build_oids(self):

        if not self.oid_tree:
            return None, None

        oids_dict, var_binds = \
            self._build_oid_recursively('', self.oid_tree[SNMP_TREE],
                                        {}, [], 0)

        oids_dict = {key: oids_dict[key][1:] for key in oids_dict}

        return oids_dict, var_binds

    def _build_oid_recursively(self, oid, curr, oids_dict,
                               var_binds, is_with_val):

        for key in curr:
            new_oid = oid + '.' + curr[key][OID]
            next_node = curr[key].get(NEXT)
            if not next_node:
                if is_with_val:
                    var_binds.append(key)
                oids_dict[key] = new_oid
            else:
                with_val = curr[key].get(WITH_VALS, 0)
                self._build_oid_recursively(new_oid, next_node, oids_dict,
                                            var_binds, with_val)

        return oids_dict, var_binds

    def _get_var_binds(self, alert_values):

        var_binds = [(self.oids[field],
                      OctetString(alert_values.get(field, NA)))
                     for field in self.var_fields]

        return var_binds

    def _get_alert_oid(self, alert_oid, severity_oid):

        sev_oid = self.oids.get(SEVERITY)
        alarm_oid = self.oids.get(ALARM_OID)

        if not (sev_oid or alarm_oid):
            LOG.error("Vitrage snmp Error: snmp tree incorrect format")
            return None

        if severity_oid:
            oid = sev_oid.replace('..', alert_oid + '.' + severity_oid)
            return oid
        else:
            oid = alarm_oid[:-1] + alert_oid

        return oid

    def _get_severity_oid(self, alert_values):

        severity_mapping = self.oid_tree.get(SEVERITY_MAPPING)

        if not severity_mapping:
            return None

        alarm_severity = alert_values.get(VProps.VITRAGE_OPERATIONAL_SEVERITY)
        state = alert_values.get(VProps.STATE)

        if state in severity_mapping:
            return severity_mapping[state]
        elif alarm_severity in severity_mapping:
            return severity_mapping[alarm_severity]

        else:
            LOG.debug('Vitrage snmp Debug: Unsupported alarm severity')
            return None

    @staticmethod
    def _send_snmp_trap(host, var_binds, alarm_oid):

        host_details = host['host']

        send_to = str(host_details.get('send_to'))
        port = str(host_details.get('port', 162))
        community_str = host_details.get('community', 'public')

        if not (send_to and IP_PAT.match(send_to) and PORT_PAT.match(port)):
            LOG.info("Vitrage snmp Info: an SNMP target host was not"
                     " configured correctly")
            return

        LOG.debug("Vitrage snmp Debug: Trap parameters: send_to: %s, "
                  "port: %s, community string: %s" %
                  (send_to, port, community_str))

        error_indication, error_status, error_index, var_bins = next(
            sendNotification(
                SnmpEngine(),
                CommunityData(community_str, mpModel=1),
                UdpTransportTarget((send_to, port)),
                ContextData(),
                'trap',
                NotificationType(
                    ObjectIdentity(alarm_oid),
                ).addVarBinds(*var_binds)
            )
        )

        if error_indication:
            LOG.error('Vitrage snmp Error: Notification not sent: %s' %
                      error_indication)
        elif error_status:
            LOG.error('Vitrage snmp Error: Notification Receiver '
                      'returned error: %s @%s' %
                      (error_status, error_index))
