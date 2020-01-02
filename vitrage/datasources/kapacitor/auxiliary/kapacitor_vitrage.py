#!/usr/bin/env python

# coding: utf-8

# Copyright 2019 - Viettel
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
import json
import logging
from logging.handlers import RotatingFileHandler
from oslo_config import cfg
import oslo_messaging as messaging
from oslo_utils import uuidutils
import socket
import sys

'''
Expected input:
Send To: rabbit://userrabbit:passrabbit@rabbit_host:5672/
EVENT_TYPE: {ALARM.STATUS} || kapacitor.alarm.critical warning info or ok
Alarm:
    id: mem high-host=controller
    message: mem high
    details: {{ .Level }} {{alarm_name}}...
    times: 2019-04-10T12:18:00Z
    duration: 0
    priority: CRITICAL
    previousLevel: OK
    host: host1
'''


LOG_FILE = '/var/log/kapacitor/kapacitor_vitrage.log'
LOG_MAX_SIZE = 10000000
LOG_FORMAT = '%(asctime)s.%(msecs).03d %(name)s[%(process)d] ' \
             '%(threadName)s %(levelname)s - %(message)s'
LOG_DATE_FMT = '%Y.%m.%d %H:%M:%S'
KAPACITOR_EVENT_TYPE = 'kapacitor.alarm'

debug = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sendto', help='url')
    args = parser.parse_args()
    data = sys.stdin.readlines()[0]
    transport_url = args.sendto
    transport = messaging.get_notification_transport(cfg.CONF, transport_url)

    driver = 'messagingv2'
    publisher = 'kapacitor_%s' % socket.gethostname()
    notifier = messaging.Notifier(transport,
                                  driver=driver,
                                  publisher_id=publisher,
                                  topics=['vitrage_notifications'])
    alarm = json.loads(data)
    host = alarm['data']['series'][0]['tags']['host']
    priority = alarm['level'].lower()
    alarm.update({'host': host,
                  'priority': priority})
    alarm.pop('data', None)
    alarm_status = alarm['level'].lower()
    event_type = '%s.%s' % (KAPACITOR_EVENT_TYPE, alarm_status)
    logging.info('Send to: %s', transport_url)
    logging.info('BODY:\n----\n%s\n', data)
    logging.info('PUBLISHER: %s', publisher)
    logging.info('EVENT_TYPE: %s', event_type)
    logging.info('\nALARM:\n%s', alarm)
    notifier.info(ctxt={'message_id': uuidutils.generate_uuid(),
                        'publisher_id': publisher},
                  event_type=event_type,
                  payload=alarm)
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
