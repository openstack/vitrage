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


class DoctorProperties(object):
    TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
    HOST_DOWN = 'compute.host.down'
    HOST_TYPE = 'nova.host'
    TYPE = 'type'
    TIME = 'time'
    UPDATE_TIME = 'update_time'
    DETAILS = 'details'


class DoctorDetails(object):
    """The details appear inside a details section in the event """
    HOSTNAME = 'hostname'
    STATUS = 'status'
    SEVERITY = 'severity'


class DoctorStatus(object):
    DOWN = 'down'
    UP = 'up'


def get_detail(alarm, detail):
    return alarm[DoctorProperties.DETAILS][detail] if \
        alarm and DoctorProperties.DETAILS in alarm and \
        detail in alarm[DoctorProperties.DETAILS] \
        else None
