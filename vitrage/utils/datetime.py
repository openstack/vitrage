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

from datetime import datetime
from datetime import timedelta
from dateutil import parser
from oslo_utils import timeutils


TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def utcnow(with_timezone=True):
    """Better version of utcnow() that returns utcnow with a correct TZ."""
    return timeutils.utcnow(with_timezone)


def format_utcnow(with_timezone=True, date_format=TIMESTAMP_FORMAT):
    return utcnow(with_timezone).strftime(date_format)


def change_time_str_format(timestamp_str, old_format, new_format):
    utc = datetime.strptime(timestamp_str, old_format)
    return utc.strftime(new_format)


def change_to_utc_time_and_format(timestamp_str, new_format):
    timestamp = parser.parse(timestamp_str)
    timestamp = timestamp - timedelta(seconds=(
        datetime.now() - datetime.utcnow()).total_seconds())
    return timestamp.strftime(new_format)


def format_unix_timestamp(timestamp, date_format=TIMESTAMP_FORMAT):
    return datetime.fromtimestamp(float(timestamp)) \
        .strftime(date_format)


def format_timestamp(timestamp_str, new_format=TIMESTAMP_FORMAT):
    return parser.parse(timestamp_str).strftime(new_format) if timestamp_str \
        else None


def datetime_delta(delta_seconds,
                   time_to_use=None,
                   with_timezone=True,
                   date_format=TIMESTAMP_FORMAT):
    if time_to_use:
        t = time_to_use
    else:
        t = utcnow(with_timezone)

    return (t + timedelta(seconds=delta_seconds)).strftime(date_format)
