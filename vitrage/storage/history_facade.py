# Copyright 2018 - Nokia
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

import pytz
import sqlalchemy
from sqlalchemy import and_
from sqlalchemy import or_

from oslo_db.sqlalchemy import utils as sqlalchemyutils
from oslo_log import log
from oslo_utils import timeutils

from vitrage.common.constants import EdgeLabel as ELabel
from vitrage.common.constants import HistoryProps as HProps
from vitrage.common.exception import VitrageInputError
from vitrage.entity_graph.mappings.operational_alarm_severity import \
    OperationalAlarmSeverity as OSeverity
from vitrage.storage import db_time
from vitrage.storage.sqlalchemy import models

LOG = log.getLogger(__name__)


LIMIT = 10000
ASC = 'asc'
DESC = 'desc'


class HistoryFacadeConnection(object):
    def __init__(self, engine_facade, alarms, edges, changes):
        self._engine_facade = engine_facade
        self._alarms = alarms
        self._edges = edges
        self._changes = changes

    def disable_alarms_in_history(self):
        end_time = db_time()
        active_alarms = self.get_alarms(limit=0)
        changes_to_add = [alarm.vitrage_id for alarm in active_alarms]
        self._alarms.end_all_alarms(end_time)
        self._edges.end_all_edges(end_time)
        self._changes.add_end_changes(changes_to_add, end_time)

    @staticmethod
    def add_utc_timezone(time):
        time = pytz.utc.localize(time)
        return time

    def count_active_alarms(self, project_id=None, is_admin_project=False):

        session = self._engine_facade.get_session()
        query = session.query(models.Alarm)
        query = query.filter(models.Alarm.end_timestamp > db_time())
        query = self._add_project_filtering_to_query(
            query, project_id, is_admin_project)

        query_severe = query.filter(
            models.Alarm.vitrage_operational_severity == OSeverity.SEVERE)
        query_critical = query.filter(
            models.Alarm.vitrage_operational_severity == OSeverity.CRITICAL)
        query_warning = query.filter(
            models.Alarm.vitrage_operational_severity == OSeverity.WARNING)
        query_ok = query.filter(
            models.Alarm.vitrage_operational_severity == OSeverity.OK)
        query_na = query.filter(
            models.Alarm.vitrage_operational_severity == OSeverity.NA)

        counts = {OSeverity.SEVERE: query_severe.count(),
                  OSeverity.CRITICAL: query_critical.count(),
                  OSeverity.WARNING: query_warning.count(),
                  OSeverity.OK: query_ok.count(),
                  OSeverity.NA: query_na.count()}

        return counts

    def get_alarms(self,
                   start=None,
                   end=None,
                   limit=LIMIT,
                   sort_by=(HProps.START_TIMESTAMP, HProps.VITRAGE_ID),
                   sort_dirs=(ASC, ASC),
                   filter_by=None,
                   filter_vals=None,
                   next_page=True,
                   marker=None,
                   only_active_alarms=False,
                   project_id=None,
                   is_admin_project=False):
        """Return alarms that match all filters sorted by the given keys.

        Deleted alarms will be returned when only_active_alarms=False.

        filtering and sorting are possible on each row of alarms table
        (pay attantion: it is not recommended to filter by start_timestamp
        and end_timestamp when start or end arguments are passed):
        vitrage_id,
        start_timestamp,
        end_timestamp,
        name,
        vitrage_type,
        vitrage_aggregated_severity,
        project_id,
        vitrage_resource_type,
        vitrage_resource_id,
        vitrage_resource_project_id,
        payload

        Time Frame:
        start and end arguments gives the time frame for required alarms.
        Required format is the format that can be parsed by timeutils library.
        If both arguments are given, returned alarms are the alarms that
        where active sometime during given time frame
        (including active and inactive alarms):

        1.  start_ts------------end_ts
        2.                   start_ts------------end_ts
        3.                                  start_ts------------end_ts
        4.      start_ts---------------------------------------end_ts
                        start                            end
                          |_______________________________|

        If only start is given, all alarms that started after this time
        will be returned (including active and inactive alarms):
        1.                   start_ts------------end_ts
        2.                                  start_ts------
                        start                            now
                          |_______________________________|

        note1: end argument can't be used without start argument
        note2: time frame can't be used with flag only_active_alarms=True

        Filtering:
        filter_by represents parameters to filter on,
        and filter_vals contains the values to filter on in corresponding
        order to the order of parameters in filter_by.
        The filtering is according to SQL 'like' statement.
        It's possible to filter on each row of alarms table
        The filtering is also possible on list of values.

        examples:
        1. In the following example:
            |   filter_by = ['vitrage_type', 'vitrage_resource_type']
            |   filter_vals = ['zabbix', 'nova']
            which will be evaluated to:
                Alarm.vitrage_type like '%zabbix%'
                and Alarm.vitrage_resource_type like '%nova%'
            Tthe filtering will be done so the query returns all the alarms
            in the DB with vitrage type containing the string 'zabbix'
            and vitrage resource type containing the string 'nova'

        2. Following example is filtering list of values for one same property:
            |   filter_by = ['vitrage_type', 'vitrage_id']
            |   filter_vals = ['zabbix', ['123', '456', '789']]
            It will be evaluated to:
                Alarm.vitrage_type like '%zabbix%'
                and Alarm.vitrage_resource_type like '%123%'
                    or like '%456%'
                    or like '%789%'
            Tthe filtering will be done so the query returns all the alarms
            in the DB with vitrage type containing the string 'zabbix'
            and with one of vitrage_ids that are in the list in filter_vals[1]


        :param start: start of time frame
        :param end: end of time frame
        :param limit: maximum number of items to return,
        if limit=0 the method will return all matched items in alarms table,
        if limit is bigger then default parameter LIMIT, the number of items
        that will be returned will be defined by the default parameter LIMIT
        :param sort_by: array of attributes by which results should be sorted
        :param sort_dirs: per-column array of sort_dirs,
        corresponding to sort_keys ('asc' or 'desc').
        :param filter_by: array of attributes by which results will be filtered
        :param filter_vals: per-column array of filter values
        corresponding to filter_by
        :param next_page: if True will return next page when marker is given,
         if False will return previous page when marker is given,
         otherwise, returns first page if no marker was given.
        :param marker: if None returns first page, else if vitrage_id is given
        and next_page is True, return next #limit results after marker,
        else, if next page is False,return #limit results before marker.
        :param only_active_alarms: if True, returns only active alarms,
        if False return active and non-active alarms.
        :param project_id: if None there is no filtering by project_id
        (equals to All Tenants=True),
        if id is given, query will be fillter alarms by project id.
        :param is_admin_project: True to return alarms with
        project_id=None or resource_project_id=None
        """

        session = self._engine_facade.get_session()
        query = session.query(models.Alarm)
        query = self._add_project_filtering_to_query(
            query, project_id, is_admin_project)

        self.assert_args(start, end, filter_by, filter_vals,
                         only_active_alarms, sort_dirs)

        if only_active_alarms:
            query = query.filter(models.Alarm.end_timestamp > db_time())
        elif (start and end) or start:
            query = self._add_time_frame_to_query(query, start, end)

        query = self._add_filtering_to_query(query, filter_by, filter_vals)

        if limit:
            query = self._generate_alarms_paginate_query(query,
                                                         limit,
                                                         sort_by,
                                                         sort_dirs,
                                                         next_page,
                                                         marker)
        elif limit == 0:
            sort_dir_func = {
                ASC: sqlalchemy.asc,
                DESC: sqlalchemy.desc,
            }
            for i in range(len(sort_by)):
                query.order_by(sort_dir_func[sort_dirs[i]](
                    getattr(models.Alarm, sort_by[i])))
        return query.all()

    @staticmethod
    def assert_args(start,
                    end,
                    filter_by,
                    filter_vals,
                    only_active_alarms,
                    sort_dirs):
        if only_active_alarms and (start or end):
            raise VitrageInputError("'only_active_alarms' can't be used "
                                    "with 'start' or 'end' ")
        if end and not start:
            raise VitrageInputError("'end' can't be used without 'start'")
        if (filter_by and not filter_vals) or (filter_vals and not filter_by):
            raise VitrageInputError('Cannot perform filtering, one of '
                                    'filter_by or filter_vals are missing')
        if filter_by and filter_vals and len(filter_by) != len(filter_vals):
            raise VitrageInputError("Cannot perform filtering, len of "
                                    "'filter_by' and 'filter_vals' differs")
        for d in sort_dirs:
            if d not in (ASC, DESC):
                raise VitrageInputError("Unknown sort direction %s" % d)

    @staticmethod
    def _add_time_frame_to_query(query, start, end):
        start = timeutils.normalize_time(start)
        if start and end:
            end = timeutils.normalize_time(end)
            query = \
                query.filter(
                    or_(and_(models.Alarm.start_timestamp >= start,
                             models.Alarm.start_timestamp <= end),
                        and_(models.Alarm.end_timestamp >= start,
                             models.Alarm.end_timestamp <= end),
                        and_(models.Alarm.start_timestamp <= start,
                             models.Alarm.end_timestamp >= end)))
        elif start:
            query = query.filter(models.Alarm.end_timestamp >= start)
        return query

    @staticmethod
    def _add_project_filtering_to_query(query, project_id=None,
                                        is_admin_project=False):

        if project_id:
            if is_admin_project:
                query = query.filter(or_(
                    or_(models.Alarm.project_id == project_id,
                        models.Alarm.vitrage_resource_project_id ==
                        project_id),
                    and_(
                        or_(
                            models.Alarm.project_id == project_id,
                            models.Alarm.project_id == None),
                        or_(
                            models.Alarm.vitrage_resource_project_id ==
                            project_id,
                            models.Alarm.vitrage_resource_project_id == None)
                    )))  # noqa
            else:
                query = query.filter(
                    or_(models.Alarm.project_id == project_id,
                        models.Alarm.vitrage_resource_project_id ==
                        project_id))
        return query

    @staticmethod
    def _add_filtering_to_query(query, filter_by, filter_vals):

        if not (filter_by or filter_vals):
            return query

        for i in range(len(filter_by)):
            key = filter_by[i]
            val = filter_vals[i]
            val = val if val and type(val) == list else [val]
            cond = or_(*[getattr(models.Alarm, key).like(
                '%' + val[j] + '%') for j in range(len(val))])
            query = query.filter(cond)
        return query

    def _generate_alarms_paginate_query(self,
                                        query,
                                        limit,
                                        sort_by,
                                        sort_dirs,
                                        next_page,
                                        marker):

        limit = min(int(limit), LIMIT)

        if marker:
            session = self._engine_facade.get_session()
            marker = session.query(models.Alarm). \
                filter(models.Alarm.vitrage_id ==
                       marker).first()

        if HProps.VITRAGE_ID not in sort_by:
            sort_by.append(HProps.VITRAGE_ID)
            sort_dirs.append(ASC)

        if not next_page and marker:  # 'not next_page' means previous page
            marker = self._create_marker_for_prev(
                query, limit, sort_by, sort_dirs, marker)

        query = sqlalchemyutils.paginate_query(query,
                                               models.Alarm,
                                               limit,
                                               sort_by,
                                               sort_dirs=sort_dirs,
                                               marker=marker)
        return query

    @staticmethod
    def _create_marker_for_prev(query, limit, sort_by, sort_dirs, marker):

        dirs = [DESC if d == ASC else ASC for d in sort_dirs]
        query = sqlalchemyutils.paginate_query(query,
                                               models.Alarm,
                                               limit + 1,
                                               sort_by,
                                               marker=marker,
                                               sort_dirs=dirs)

        alarms = query.all()
        if len(alarms) < limit + 1:
            new_marker = None
        else:
            new_marker = alarms[-1]

        return new_marker

    def alarm_rca(self,
                  alarm_id,
                  forward=True,
                  backward=True,
                  depth=None,
                  project_id=None,
                  admin=False):

        n_result_f = []
        e_result_f = []
        if forward:
            n_result_f, e_result_f = \
                self._bfs(alarm_id, self._out_rca, depth, admin=admin,
                          project_id=project_id)

        n_result_b = []
        e_result_b = []
        if backward:
            n_result_b, e_result_b = \
                self._bfs(alarm_id, self._in_rca, depth, admin=admin,
                          project_id=project_id)

        n_result = self.get_alarms(limit=0,
                                   filter_by=[HProps.VITRAGE_ID],
                                   filter_vals=[n_result_f + n_result_b])

        e_result = e_result_f + e_result_b

        return n_result, e_result

    def _rca_edges(self, filter_by, a_ids, proj_id, admin):
        alarm_ids = [str(alarm) for alarm in a_ids]
        session = self._engine_facade.get_session()
        query = session.query(models.Edge)\
            .filter(and_(getattr(models.Edge, filter_by).in_(alarm_ids),
                         models.Edge.label == ELabel.CAUSES))

        query = query.join(models.Edge.target)
        query = self._add_project_filtering_to_query(query, proj_id, admin)

        return query.all()

    def _out_rca(self, sources, proj_id, admin):
        return self._rca_edges(HProps.SOURCE_ID, sources, proj_id, admin)

    def _in_rca(self, targets, proj_id, admin):
        return self._rca_edges(HProps.TARGET_ID, targets, proj_id, admin)

    def _bfs(self, alarm_id, neighbors_func,
             depth=None,
             project_id=None,
             admin=False):
        n_result = []
        visited_nodes = set()
        n_result.append(alarm_id)
        e_result = []
        curr_depth = 0
        nodes_q = {curr_depth: [alarm_id]}
        while nodes_q:
            node_ids = nodes_q.pop(curr_depth)
            if depth and curr_depth >= depth:
                break
            for node_id in node_ids:
                if node_id in visited_nodes:
                    node_ids.remove(node_id)
            visited_nodes.update(node_ids)
            e_list = neighbors_func(node_ids, project_id, admin)
            n_list = \
                [edge.target_id if edge.source_id in node_ids
                 else edge.source_id for edge in e_list]
            n_result.extend(n_list)
            e_result.extend(e_list)
            if n_list:
                curr_depth += 1
                nodes_q[curr_depth] = n_list

        return n_result, e_result
