# Copyright 2017 - ZTE
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

import copy
from oslo_config import cfg

from pysnmp.proto.rfc1902 import Integer
from pysnmp.proto.rfc1902 import ObjectIdentifier
from pysnmp.proto.rfc1902 import ObjectName
from pysnmp.proto.rfc1902 import OctetString
from pysnmp.proto.rfc1902 import TimeTicks

from vitrage.snmp_parsing.service import SnmpParsingService
from vitrage.tests import base


BINDS_REPORTED = [
    (ObjectName('1.3.6.1.2.1.1.3.0'), TimeTicks(1491462248)),
    (ObjectName('1.3.6.1.6.3.1.1.4.1.0'),
     ObjectIdentifier('1.3.6.1.4.1.3902.4101.1.4.1.2')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.3'),
     OctetString(hexValue='07e10406070408002b0800')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.1.2'), Integer(0)),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.1.4'), Integer(0)),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.1.3'), OctetString('')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.11'), OctetString('3305115653')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.2'), OctetString('host')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.4'), Integer(1)),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.5'), Integer(14)),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.6'), Integer(0)),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.7'), OctetString('')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.8'),
     OctetString('vimid=,hid=controller_controller,'
                 'hostname=controller,'
                 'Reason: nova-compute is not available')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.12'),
     OctetString('Tecs Director')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.9'), Integer(1581)),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.1'),
     OctetString('3e7393db-2def-447c-8cba-77bf29ab29b4')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.14'),
     OctetString('compute is not available')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.15'),
     OctetString('vimid=,hostname=controller')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.16'), OctetString('')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.17'),
     OctetString('10.62.89.92')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.18'), Integer(0)),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.19'), OctetString('')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.20'),
     OctetString('Asia/Harbin')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.21'), Integer(0)),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.22'), Integer(0)),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.23'), OctetString('')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.24'), OctetString('')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.26'),
     OctetString('controller_controller')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.10'), OctetString('')),
    (ObjectName('1.3.6.1.4.1.3902.4101.1.3.1.25'), OctetString(''))
]

DICT_EXPECTED = {
    u'1.3.6.1.4.1.3902.4101.1.3.1.8':
        u'vimid=,hid=controller_controller,'
        u'hostname=controller,'
        u'Reason: nova-compute is not available',
    u'1.3.6.1.4.1.3902.4101.1.3.1.9': 1581,
    u'1.3.6.1.4.1.3902.4101.1.3.1.6': 0,
    u'1.3.6.1.4.1.3902.4101.1.3.1.7': u'',
    u'1.3.6.1.4.1.3902.4101.1.3.1.4': 1,
    u'1.3.6.1.4.1.3902.4101.1.3.1.5': 14,
    u'1.3.6.1.4.1.3902.4101.1.3.1.2': u'host',
    u'1.3.6.1.4.1.3902.4101.1.3.1.3':
        u'\x07\xe1\x04\x06\x07\x04\x08\x00+\x08\x00',
    u'1.3.6.1.4.1.3902.4101.1.3.1.1': u'3e7393db-2def-447c-8cba-77bf29ab29b4',
    u'1.3.6.1.4.1.3902.4101.1.3.1.18': 0,
    u'1.3.6.1.4.1.3902.4101.1.3.1.19': u'',
    u'1.3.6.1.4.1.3902.4101.1.3.1.10': u'',
    u'1.3.6.1.4.1.3902.4101.1.3.1.11': u'3305115653',
    u'1.3.6.1.4.1.3902.4101.1.3.1.12': u'Tecs Director',
    u'1.3.6.1.4.1.3902.4101.1.3.1.14': u'compute is not available',
    u'1.3.6.1.4.1.3902.4101.1.3.1.15': u'vimid=,hostname=controller',
    u'1.3.6.1.4.1.3902.4101.1.3.1.16': u'',
    u'1.3.6.1.4.1.3902.4101.1.3.1.17': u'10.62.89.92',
    u'1.3.6.1.4.1.3902.4101.1.1.4': 0,
    u'1.3.6.1.4.1.3902.4101.1.1.3': u'',
    u'1.3.6.1.4.1.3902.4101.1.1.2': 0,
    u'1.3.6.1.2.1.1.3.0': u'1491462248',
    u'1.3.6.1.6.3.1.1.4.1.0': u'1.3.6.1.4.1.3902.4101.1.4.1.2',
    u'1.3.6.1.4.1.3902.4101.1.3.1.25': u'',
    u'1.3.6.1.4.1.3902.4101.1.3.1.24': u'',
    u'1.3.6.1.4.1.3902.4101.1.3.1.26': u'controller_controller',
    u'1.3.6.1.4.1.3902.4101.1.3.1.21': 0,
    u'1.3.6.1.4.1.3902.4101.1.3.1.20': u'Asia/Harbin',
    u'1.3.6.1.4.1.3902.4101.1.3.1.23': u'',
    u'1.3.6.1.4.1.3902.4101.1.3.1.22': 0
}


class TestSnmpParsing(base.BaseTest):
    OPTS = [
        cfg.IntOpt('snmp_listening_port', default=8162,
                   help='The listening port of snmp_parsing service'),
        cfg.StrOpt('oid_mapping',
                   default='vitrage/tests/resources/snmp_parsing/'
                           'snmp_parsing_conf.yaml',
                   help='The default path of oid_mapping yaml file'),
    ]

    # noinspection PyPep8Naming
    @classmethod
    def setUpClass(cls):
        super(TestSnmpParsing, cls).setUpClass()
        cls.conf = cfg.ConfigOpts()
        cls.conf.register_opts(cls.OPTS, group='snmp_parsing')
        cls.conf.register_opt(
            cfg.StrOpt('backend_url', default='zake://'), group='coordination'
        )

    def test_convert_binds_to_dict(self):
        parsing_service = SnmpParsingService(1, self.conf)
        dict_converted = parsing_service._convert_binds_to_dict(BINDS_REPORTED)
        self.assert_dict_equal(dict_converted, DICT_EXPECTED)

    def test_get_event_type(self):
        parsing_service = SnmpParsingService(1, self.conf)
        event_type = parsing_service._get_event_type(DICT_EXPECTED)
        self.assertEqual(event_type, 'vitrage.snmp.event')

    def test_converted_trap_mapping_diff_system(self):
        converted_trap_diff_sys = copy.copy(DICT_EXPECTED)
        converted_trap_diff_sys.update(
            {u'1.3.6.1.4.1.3902.4101.1.3.1.12': u'Different System'})
        parsing_service = SnmpParsingService(1, self.conf)
        event_type = parsing_service._get_event_type(converted_trap_diff_sys)
        self.assertIsNone(event_type)
