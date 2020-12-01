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
import json
import socket

from collections import namedtuple
from ipaddress import ip_address
from oslo_config import cfg
from oslo_log import log
import requests
from urllib import parse as urlparse

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import EventProperties as EProps
from vitrage.datasources.alarm_driver_base import AlarmDriverBase
from vitrage.datasources.prometheus import PROMETHEUS_DATASOURCE
from vitrage.datasources.prometheus.properties import get_alarm_update_time
from vitrage.datasources.prometheus.properties import get_label
from vitrage.datasources.prometheus.properties import PrometheusAlertLabels \
    as PAlertLabels
from vitrage.datasources.prometheus.properties \
    import PrometheusAlertProperties as PAlertProps
from vitrage.datasources.prometheus.properties import PrometheusAlertStatus \
    as PAlertStatus
from vitrage.datasources.prometheus.properties \
    import PrometheusConfigFileProperties as PCFProps
from vitrage.datasources.prometheus.properties \
    import PrometheusDatasourceProperties as PDProps
from vitrage.datasources.prometheus.properties \
    import PrometheusGetAllProperties as PGAProps
from vitrage.datasources.prometheus.properties \
    import PrometheusProperties as PProps
from vitrage import os_clients
from vitrage.utils import file as file_utils

CONF = cfg.CONF
LOG = log.getLogger(__name__)

PROMETHEUS_EVENT_TYPE = 'prometheus.alarm'


class PrometheusDriver(AlarmDriverBase):
    """Handle Prometheus events.

    Prometheus driver uses a configuration file that maps
    the Prometheus alert labels to a corresponding Vitrage resource
    with specific properties (id or other unique properties).
    The mapping will most likely be defined by the alert name and other fields.

    Prometheus configuration file structure:
    The configuration file contains a list of alerts.
    Each alert contains key and resource.

    The key contains labels which uniquely identify each alert.

    The resource specifies how to identify in Vitrage the resource that
    the alert is on. It contains one or more Vitrage property names and
    corresponding Prometheus alert labels.

    Example:
    ^^^^^^^^
        Prometheus event's details:
        ---------------------------
            {
              "status": "firing",
              "version": "4",
              "groupLabels": {
                "alertname": "HighCpuOnVmAlert"
              },
              "commonAnnotations": {
                "description": "Test alert to test libvirt exporter.\n",
                "title": "High cpu usage on vm"
              },
              "groupKey": "{}:{alertname=\"HighCpuOnVmAlert\"}",
              "receiver": "vitrage",
              "externalURL": "http://vitrage.is.the.best:9093",
              "alerts": [
                {
                  "status": "firing",
                  "labels": {
                    "instance": "1.1.1.1:9999",
                    "domain": "instance-00000004",
                    "job": "libvirt",
                    "alertname": "HighCpuOnVmAlert",
                    "severity": "critical"
                  },
                  "endsAt": "2019-01-16T12:26:05.91446215Z",
                  "generatorURL": "http://seriously.vitrage.is.the.best",
                  "startsAt": "2019-01-16T12:11:50.91446215Z",
                  "annotations": {
                    "description": "Test alert to test libvirt exporter.\n",
                    "title": "High cpu usage on vm"
                  }
                },
              ],
              "commonLabels": {
                "instance": "1.1.1.1:9999",
                "job": "libvirt",
                "severity": "critical",
                "alertname": "HighCpuOnVmAlert"
              }
            }


        prometheus_conf.yaml:
        ---------------------
            alerts:
            - key:
                alertname: HighCpuOnVmAlert
                job: libvirt
              resource:
                instance_name: domain
                host_id: instance


    `enrich_event` functions are explained based on the example above.
    """

    AlarmKey = namedtuple('AlarmKey', [PAlertLabels.ALERT_NAME,
                                       PCFProps.RESOURCE])
    conf_map = {}

    def __init__(self):
        super(PrometheusDriver, self).__init__()
        self._client = None
        self._nova_client = None
        self.conf_map = self._configuration_mapping()

    @property
    def nova_client(self):
        if not self._nova_client:
            self._nova_client = os_clients.nova_client()
        return self._nova_client

    def _vitrage_type(self):
        return PROMETHEUS_DATASOURCE

    def _alarm_key(self, alert):
        return self.AlarmKey(
            alertname=get_label(alert, PAlertLabels.ALERT_NAME),
            resource=str(self._get_resource_alert_values(alert)))

    def _is_erroneous(self, alert):
        return alert and PAlertStatus.FIRING == alert.get(PAlertProps.STATUS)

    def _is_valid(self, alert):
        if not alert or PAlertProps.STATUS not in alert:
            return False
        return True

    def _status_changed(self, new_alarm, old_alarm):
        return \
            new_alarm.get(PAlertProps.STATUS) != \
            old_alarm.get(PAlertProps.STATUS)

    def _get_all_alarms(self):
        alertmanager_url = CONF.prometheus.alertmanager_url
        receiver = CONF.prometheus.receiver
        if not alertmanager_url:
            LOG.warning('Alertmanager url is not defined')
            return []

        if not receiver:
            LOG.warning('Receiver is not defined')
            return []

        payload = {PGAProps.ACTIVE: 'true',
                   PGAProps.RECEIVER: receiver}

        session = requests.Session()

        response = session.get(alertmanager_url,
                               params=payload)

        if response.status_code == requests.codes.ok:
            if 'v1' in alertmanager_url:
                alerts = json.loads(response.text)[PGAProps.DATA]
            else:
                alerts = json.loads(response.text)
            self._modify_alert_status(alerts)
            alarms = self._enrich_alerts(alerts, PROMETHEUS_EVENT_TYPE)
            return alarms
        else:
            LOG.error('Failed to get Alertmanager data. Response code: %s',
                      response.status_code)
        return []

    @staticmethod
    def _modify_alert_status(alerts):
        for alert in alerts:
            if alert.get(PAlertProps.STATUS).get(PGAProps.STATE) == \
                    PGAProps.ACTIVE:
                alert[PAlertProps.STATUS] = PAlertStatus.FIRING

    def _get_changed_alarms(self):
        return []

    @staticmethod
    def _configuration_mapping():
        prometheus_config_file = CONF.prometheus[DSOpts.CONFIG_FILE]
        try:
            prometheus_config = \
                file_utils.load_yaml_file(prometheus_config_file)
            return prometheus_config[PCFProps.ALERTS]
        except Exception:
            LOG.exception('Failed in init the configuration file: %s',
                          prometheus_config_file)
            return {}

    def enrich_event(self, event, event_type):
        """Get an alert event from Prometheus and create a list of alert events

        :param event: Prometheus event.
        :param event_type: The type of the event. Always 'prometheus.alert'.
        :return: a list of alarms, one per Prometheus alert

        For the example above. The function returns:
            {
              "status": "firing",
              "labels": {
                "instance": "1.1.1.1:9999",
                "domain": "instance-00000004",
                "job": "libvirt",
                "alertname": "HighCpuOnVmAlert",
                "severity": "critical"
              },
              "vitrage_entity_type": "prometheus",
              "endsAt": "2019-01-16T12:39:50.91446215Z",
              "generatorURL": "http://seriously.vitrage.is.the.best",
              "vitrage_datasource_name": "prometheus",
              "startsAt": "2019-01-16T12:11:50.91446215Z",
              "vitrage_datasource_action": "update",
              "vitrage_entity_unique_props": {
                "instance_name": "instance-00000004",
                "host_id": "my-host-name"
              },
              "vitrage_sample_date": "2019-01-16T13:10:33Z",
              "vitrage_event_type": "prometheus.alarm",
              "annotations": {
                "description": "Test alert to test libvirt exporter.\n",
                "title": "High cpu usage on vm"
              }
            }

        """

        LOG.debug('Going to enrich event: %s', event)

        alarms = []
        details = event.get(EProps.DETAILS)
        if details:
            alarms = self._enrich_alerts(details.get(PProps.ALERTS, []),
                                         event_type)

        LOG.debug('Enriched event. Created alert events: %s', alarms)

        return self.make_pickleable(alarms, PROMETHEUS_DATASOURCE,
                                    DatasourceAction.UPDATE)

    def _enrich_alerts(self, alerts, event_type):
        return [self._enrich_alert(alert, event_type) for alert in alerts]

    def _enrich_alert(self, alert, event_type):
        """Enrich prometheus alert.

        Adding fields to prometheus alert in order to map it to vitrage entity.

        :param alert: Prometheus alert
        :param event_type: The type of the event. Always 'prometheus.alert'.
        :return: Enriched prometheus alert
        """
        alert[DSProps.EVENT_TYPE] = event_type
        vitrage_entity_unique_props = \
            self._calculate_vitrage_entity_unique_props(alert)
        alert[PDProps.ENTITY_UNIQUE_PROPS] = \
            vitrage_entity_unique_props
        old_alarm = self._old_alarm(alert)
        alert = self._filter_and_cache_alarm(
            alert, old_alarm,
            self._filter_get_erroneous,
            get_alarm_update_time(alert))
        return alert

    def _calculate_vitrage_entity_unique_props(self, alert):
        """Build a vitrage entity unique props.

        The unique props are based on the alert and the conf file.

        :param alert: Prometheus alert
        :type alert: dict
        :return: Unique properties of vitrage entity
        ":rtype: dict

        For the example above. The function returns:
            {'instance_name': 'instance-00000004',
            'host_id': 'my-host-name'}
        """
        resource_labels = self._get_conf_resource(alert)
        vitrage_entity_unique_props = {}
        for vitrage_label in resource_labels:
            prometheus_label = resource_labels[vitrage_label]
            label_value = str(get_label(alert, prometheus_label))
            vitrage_entity_unique_props[vitrage_label] = \
                self._adjust_label_value(label_value)
        return vitrage_entity_unique_props

    def _adjust_label_value(self, label_value):
        """Adjust the given value of the alert's label

        First check if the value is ip.
        Then, get its hostname if it has one.
        If not, fetch the instance id from nova by its ip.
        Otherwise, leave the label value as is.

        :param label_value: Value of alert's label
        :type label_value: str
        :return: Adjusted label's value of the alert as described.
        :rtype: str

        For the example above. The function returns:
          - label_value='instance-00000004' it returns:'instance-00000004'
          - label_value='1.1.1.1:9999' it returns:'my-host-name'
        """
        if label_value is not None:
            try:
                # Check if the value is ip
                ip = str(self._validate_ip(label_value))
                try:
                    # Get hostname of the ip
                    entity_hostname = socket.gethostbyaddr(ip)
                    label_value = entity_hostname[0]

                except socket.error:
                    # If not ip of a host
                    nova_instance = self.nova_client.servers.list(
                        search_opts={'all_tenants': 1, 'ip': ip})
                    if nova_instance:
                        label_value = nova_instance[0].id
                    else:
                        label_value = ip

            except ValueError:
                # If not ip value, leave it as is
                pass

        return label_value

    def _get_resource_alert_values(self, alert):
        """Get values of the alert labels from alert's resource in config file.

        For the example above. The function returns:
            {'instance': '1.1.1.1:9999', 'domain': 'instance-00000004'}
        """

        resource_alert_labels = self._get_conf_resource(alert).values()
        alert_values = {label: get_label(alert, label)
                        for label in resource_alert_labels}
        return alert_values

    def _get_conf_resource(self, alert):
        """Get resource from conf file that matches the alert.

        Matching a resource from conf file to alert is done by
        alert's key in the conf file.
        The alert's key in conf file contains alert's labels and
        their value as in Prometheus alert.

        :param alert: Prometheus alert
        :type alert: dict
        :return: Resource that matches the alert
        :rtype: dict

        Resource is a dict, where the keys are vitrage entity fields
        and its values are the corresponding alert labels.

        For the example above. The function returns:
          {'instance_name': 'domain', 'host_id': 'instance'}
        """
        if self.conf_map:
            for conf_alert in self.conf_map:
                alert_key = conf_alert[PCFProps.KEY].items()
                alert_labels = alert[PAlertProps.LABELS].items()
                match = set(alert_key).issubset(set(alert_labels))
                if match:
                    return conf_alert[PCFProps.RESOURCE]
        return {}

    @staticmethod
    def _validate_ip(value):
        """Check if the value is ip address.

        If the value is in ip:port form, separate it and validate just the ip.

        :param value: String value
        :return:An IPv4Address or IPv6Address object
        :raises ValueError: if the *value* passed isn't either a v4 or a v6
        address
        """
        # check if the value is ip
        try:
            ip = ip_address(str(value))
        except ValueError:
            parsed = urlparse.urlparse('//{}'.format(value))
            ip = ip_address(str(parsed.hostname))
        return ip

    @staticmethod
    def get_event_types():
        return [PROMETHEUS_EVENT_TYPE]

    @staticmethod
    def should_delete_outdated_entities():
        return True
