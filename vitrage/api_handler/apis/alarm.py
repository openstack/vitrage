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
from dateutil import parser
import json

from oslo_log import log
from osprofiler import profiler

from vitrage.api_handler.apis import base
from vitrage.common.constants import EntityCategory as ECategory
from vitrage.common.constants import HistoryProps as HProps
from vitrage.common.constants import TenantProps
from vitrage.common.constants import VertexProperties as VProps
from vitrage.common.utils import compress_obj
from vitrage.datasources.alarm_properties import AlarmProperties as AProps
from vitrage.entity_graph.mappings.operational_alarm_severity import \
    OperationalAlarmSeverity
from vitrage.storage import db_time

LOG = log.getLogger(__name__)


@profiler.trace_cls("alarm apis",
                    info={}, hide_args=False, trace_private=False)
class AlarmApis(base.EntityGraphApisBase):

    @base.lock_graph
    def get_alarms(self, ctx, vitrage_id, all_tenants, *args, **kwargs):

        kwargs = self._parse_kwargs(kwargs)

        if not vitrage_id or vitrage_id == 'all':
            if not all_tenants:
                kwargs['project_id'] = \
                    ctx.get(TenantProps.PROJECT_ID, 'no-project')
                kwargs['is_admin_project'] = \
                    ctx.get(TenantProps.IS_ADMIN, False)
        else:
            kwargs.get('filter_by', []).append(VProps.VITRAGE_RESOURCE_ID)
            kwargs.get('filter_vals', []).append(vitrage_id)

        alarms = self._get_alarms(*args, **kwargs)
        data = {'alarms': [v.payload for v in alarms]}
        return compress_obj(data, level=1)

    # TODO(annarez): add db support
    @base.lock_graph
    def show_alarm(self, ctx, vitrage_id):
        LOG.debug('Show alarm with vitrage_id: %s', vitrage_id)

        alarm = self.entity_graph.get_vertex(vitrage_id)
        if not alarm or alarm.get(VProps.VITRAGE_CATEGORY) != ECategory.ALARM:
            LOG.warning('Alarm show - Not found (%s)', vitrage_id)
            return None

        is_admin = ctx.get(TenantProps.IS_ADMIN, False)
        curr_project = ctx.get(TenantProps.PROJECT_ID, None)
        alarm_project = alarm.get(VProps.PROJECT_ID)
        if not is_admin and curr_project != alarm_project:
            LOG.warning('Alarm show - Authorization failed (%s)', vitrage_id)
            return None

        return json.dumps(alarm.properties)

    @base.lock_graph
    def get_alarm_counts(self, ctx, all_tenants):
        LOG.debug("AlarmApis get_alarm_counts - all_tenants=%s", all_tenants)

        project_id = ctx.get(TenantProps.PROJECT_ID, None)
        is_admin_project = ctx.get(TenantProps.IS_ADMIN, False)

        if all_tenants:
            counts = self.db.history_facade.count_active_alarms()

        else:
            counts = self.db.history_facade.count_active_alarms(
                project_id=project_id,
                is_admin_project=is_admin_project)

        return json.dumps(counts)

    def _get_alarms(self, *args, **kwargs):
        """Finds all the alarms with project_id

        Finds all the alarms which has the project_id. In case the tenant is
        admin then project_id can also be None.

        :rtype: list
        """
        alarms = self.db.history_facade.get_alarms(*args, **kwargs)

        for alarm in alarms:
            start_timestamp = \
                self.db.history_facade.add_utc_timezone(alarm.start_timestamp)
            alarm.payload[HProps.START_TIMESTAMP] = str(start_timestamp)
            if alarm.end_timestamp <= db_time():
                end_timestamp = \
                    self.db.history_facade.add_utc_timezone(
                        alarm.end_timestamp)
                alarm.payload[HProps.END_TIMESTAMP] = str(end_timestamp)
                # change operational severity of ended alarms to 'OK'
                # TODO(annarez): in next version use only 'state'
                alarm.payload[VProps.VITRAGE_OPERATIONAL_SEVERITY] = \
                    OperationalAlarmSeverity.OK
                # TODO(annarez): implement state change in processor and DB
                alarm.payload[VProps.STATE] = AProps.INACTIVE_STATE

        return alarms

    def _parse_kwargs(self, kwargs):
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        if kwargs.get('start'):
            kwargs['start'] = parser.parse(kwargs['start'])
        if kwargs.get('end'):
            kwargs['end'] = parser.parse(kwargs['end'])
        if kwargs.get('sort_by') and type(kwargs.get('sort_by')) != list:
            kwargs['sort_by'] = [kwargs.get('sort_by')]
        if kwargs.get('sort_dirs') and type(kwargs.get('sort_dirs')) != list:
            kwargs['sort_dirs'] = [kwargs.get('sort_dirs')]
        if str(kwargs.get('next_page')).lower() == 'false':
            kwargs['next_page'] = False
        else:
            kwargs['next_page'] = True

        if kwargs.get('filter_by') and type(kwargs.get('filter_by')) != list:
            kwargs['filter_by'] = [kwargs.get('filter_by')]
        if kwargs.get('filter_vals') and type(
                kwargs.get('filter_vals')) != list:
            kwargs['filter_vals'] = [kwargs.get('filter_vals')]

        return kwargs
