# Copyright 2018 - Nokia
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


class PrometheusAlertProperties(object):
    STATUS = 'status'
    LABELS = 'labels'
    STARTS_AT = 'startsAt'
    ENDS_AT = 'endsAt'


class PrometheusAlertStatus(object):
    FIRING = 'firing'
    RESOLVED = 'resolved'


class PrometheusAlertLabels(object):
    SEVERITY = 'severity'
    INSTANCE = 'instance'
    DOMAIN = 'domain'
    INSTANCE_ID = 'instance_id'
    ALERT_NAME = 'alertname'


class PrometheusProperties(object):
    ALERTS = 'alerts'


class PrometheusConfigFileProperties(object):
    ALERTS = 'alerts'
    KEY = 'key'
    RESOURCE = 'resource'


class PrometheusDatasourceProperties(object):
    ENTITY_UNIQUE_PROPS = 'vitrage_entity_unique_props'


class PrometheusGetAllProperties(object):
    ALERTMANAGER_URL = 'alertmanager_url'
    RECEIVER = 'receiver'
    STATE = 'state'
    ACTIVE = 'active'
    DATA = 'data'


def get_alarm_update_time(alarm):
    if PrometheusAlertStatus.FIRING == \
            alarm.get(PrometheusAlertProperties.STATUS):
        return alarm.get(PrometheusAlertProperties.STARTS_AT)
    else:
        return alarm.get(PrometheusAlertProperties.ENDS_AT)


def get_label(alarm, label):
    labels = alarm.get(PrometheusAlertProperties.LABELS)
    return labels.get(label) if labels else None
