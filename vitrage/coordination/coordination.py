#  Copyright 2019 - Nokia Corporation
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
import json
import os
import psutil
import socket

import tenacity
import tooz.coordination

from oslo_config import cfg
from oslo_log import log
from oslo_utils import timeutils

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Coordinator(object):
    def __init__(self, my_id=None):
        self.backend_url = CONF.coordination.backend_url
        self.my_id = my_id or ' '.join(psutil.Process(os.getpid()).cmdline())
        self.coordinator = None
        if self.backend_url:
            self.coordinator = tooz.coordination.get_coordinator(
                self.backend_url,
                '{}_{}'.format(my_id, os.getpid()).encode("latin-1"))

    def start(self):
        if self.backend_url:
            try:
                self.coordinator.start(start_heart=True)
                LOG.info('Coordination backend started successfully.')
            except tooz.coordination.ToozError:
                LOG.exception('Error connecting to coordination backend.')

    def stop(self):
        if not self.is_active():
            return
        try:
            self.coordinator.stop()
        except tooz.coordination.ToozError:
            LOG.exception('Error connecting to coordination backend.')

    def is_active(self):
        return self.coordinator and self.coordinator.is_started

    @tenacity.retry(stop=tenacity.stop_after_attempt(5))
    def join_group(self, group_id='vitrage'):
        if not self.is_active() or not group_id:
            return

        try:
            now = timeutils.utcnow(with_timezone=True).replace(microsecond=0)
            isoformat = now.isoformat()

            capabilities = json.dumps(
                {
                    'name': self.my_id,
                    'hostname': socket.gethostname(),
                    'process': os.getpid(),
                    'created': isoformat
                }
            )
            join_req = self.coordinator.join_group(
                group_id.encode("latin-1"),
                capabilities.encode("latin-1"))
            join_req.get()

            LOG.info('Joined service group:%s, member:%s',
                     group_id, self.my_id)

            return
        except tooz.coordination.MemberAlreadyExist:
            return
        except tooz.coordination.GroupNotCreated as e:
            create_grp_req = self.coordinator.create_group(
                group_id.encode("latin-1"))

            try:
                create_grp_req.get()
            except tooz.coordination.GroupAlreadyExist:
                pass

            # Re-raise exception to join group again.
            raise e

    def leave_group(self, group_id):
        if self.is_active():
            self.coordinator.leave_group(group_id.encode("latin-1"))
            LOG.info('Left group %s', group_id)

    def get_services(self, group_id='vitrage'):
        if not self.is_active():
            return []

        while True:
            get_members_req = self.coordinator.get_members(
                group_id.encode("latin-1"))
            try:
                return [json.loads(
                    self.coordinator.get_member_capabilities(
                        group_id.encode("latin-1"),
                        member).get().decode('us-ascii'))
                        for member in get_members_req.get()]
            except tooz.coordination.GroupNotCreated:
                self.join_group(group_id)
