#!/usr/bin/env python

# coding: utf-8

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

import argparse
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from oslo_config import cfg
import oslo_messaging as messaging
from oslo_utils import uuidutils
import socket


'''
Expected input:
Send To:
Vitrage Message Bus address e.g.
rabbit://userrabbit:passrabbit@127.0.0.1:5672/
Subject: {TRIGGER.STATUS}
Message:
    host={HOST.NAME1}
    hostid={HOST.ID1}
    hostip={HOST.IP1}
    triggerid={TRIGGER.ID}
    description={TRIGGER.NAME}
    rawtext={TRIGGER.NAME.ORIG}
    expression={TRIGGER.EXPRESSION}
    value={TRIGGER.VALUE}
    priority={TRIGGER.NSEVERITY}
    lastchange={EVENT.DATE} {EVENT.TIME}
'''


LOG_FILE = '/var/log/zabbix/zabbix_vitrage.log'
LOG_MAX_SIZE = 10000000
LOG_FORMAT = '%(asctime)s.%(msecs).03d %(name)s[%(process)d]' \
             ' %(threadName)s %(levelname)s - %(message)s'
LOG_DATE_FMT = '%Y.%m.%d %H:%M:%S'
ZABBIX_EVENT_TYPE = 'zabbix.alarm'

debug = False


def create_payload(body):
    payload = {}
    for line in body.splitlines():
        key, prop = line.split('=', 1)
        payload[key.lower().strip()] = prop.strip()
    return payload


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('sendto', help='Vitrage message bus path')
    parser.add_argument('topic', help='zabbix topic')
    parser.add_argument('body', help='zabbix body')
    args = parser.parse_args()

    logging.info('SENDTO: %s', args.sendto)
    logging.info('TOPIC: %s', args.topic)
    logging.info('BODY:\n----\n%s\n', args.body)

    transport_url = args.sendto
    transport = messaging.get_notification_transport(cfg.CONF, transport_url)
    driver = 'messagingv2'
    publisher = 'zabbix_%s' % socket.gethostname()
    notifier = messaging.Notifier(transport,
                                  driver=driver,
                                  publisher_id=publisher,
                                  topics=['vitrage_notifications'])

    alarm_status = args.topic.lower()
    event_type = '%s.%s' % (ZABBIX_EVENT_TYPE, alarm_status)
    payload = create_payload(args.body)

    logging.info('PUBLISHER: %s', publisher)
    logging.info('EVENT_TYPE: %s', event_type)
    logging.info('\nPAYLOAD:\n%s', payload)
    notifier.info(ctxt={'message_id': uuidutils.generate_uuid(),
                        'publisher_id': publisher,
                        'timestamp': datetime.utcnow()},
                  event_type=event_type,
                  payload=payload)
    logging.info('MESSAGE SENT..')


if __name__ == '__main__':

    log = logging.getLogger()

    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)

    handler = RotatingFileHandler(filename=LOG_FILE,
                                  maxBytes=LOG_MAX_SIZE,
                                  backupCount=3)
    fmt = logging.Formatter(LOG_FORMAT, LOG_DATE_FMT)
    handler.setFormatter(fmt)
    log.addHandler(handler)

    logging.info('***----------Script start-----------***')
    try:
        main()
    except Exception as e:
        logging.exception('MESSAGE WAS NOT SENT - %s' % e)
