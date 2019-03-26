# Copyright 2016 - Nokia Corporation
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


import json
import pecan


from oslo_log import log
from osprofiler import profiler
from pecan.core import abort

from vitrage.api.controllers.v1.alarm_base import BaseAlarmsController
from vitrage.api.controllers.v1 import count
from vitrage.api.controllers.v1 import history
from vitrage.api.policy import enforce
from vitrage.common.constants import VertexProperties as Vprops


LOG = log.getLogger(__name__)


# noinspection PyBroadException
@profiler.trace_cls("alarm controller",
                    info={}, hide_args=False, trace_private=False)
class AlarmsController(BaseAlarmsController):
    count = count.AlarmCountsController()
    history = history.HistoryController()

    @pecan.expose('json')
    def get_all(self, **kwargs):

        kwargs['only_active_alarms'] = True

        LOG.info('returns alarms list with vitrage id %s',
                 kwargs.get(Vprops.VITRAGE_ID))

        return self._get_alarms(**kwargs)

    @pecan.expose('json')
    def get(self, vitrage_id):
        enforce("get alarm",
                pecan.request.headers,
                pecan.request.enforcer,
                {})

        LOG.info('returns show alarm with vitrage id %s', vitrage_id)

        return self._show_alarm(vitrage_id)

    @staticmethod
    def _show_alarm(vitrage_id):
        try:
            alarm_json = pecan.request.client.call(pecan.request.context,
                                                   'show_alarm',
                                                   vitrage_id=vitrage_id)
            LOG.info(alarm_json)
            if not alarm_json:
                abort(404, "Failed to find alarm %s" % vitrage_id)

            return json.loads(alarm_json)

        except Exception:
            LOG.exception('Failed to load JSON.')
            abort(404, 'Failed to show alarm.')
