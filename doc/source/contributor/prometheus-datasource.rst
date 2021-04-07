=====================
Prometheus Datasource
=====================

This document describes how to configure Prometheus datasource properly.
Prometheus is an open-source systems monitoring and alerting toolkit,
with exporters that export different metrics to Prometheus.
The Alertmanager handles alerts sent by Prometheus server.


Datasource configuration
========================

In order to connect Vitrage and Prometheus, configurations need to be done in both sides.


Step 1 - Configure Alertmanager
-------------------------------

Vitrage receives Prometheus alerts through event api using basic authentication.
Basic authentication is done by an Openstack administrator user.
In order to configure Prometheus to send alerts to Vitrage, add a webhook receiver in Alertmanager.

Vitrage webhook receiver example  ::

    - name: 'vitrage'
      webhook_configs:
      - url: 'http://127.0.0.1:8999/v1/event'
        send_resolved: true
        http_config:
          basic_auth:
            username: 'admin'
            password: 'admin'


``url`` is the url of Vitrage event api. This can be fetched from openstack endpoint list.
Set ``send_resolved`` to be true to ensure to get when alerts are resolved.


Step 2 - Configure Vitrage
--------------------------

In ``/etc/vitrage/vitrage.conf`` add ``prometheus`` to the list of active datasources  ::

    [datasources]
    types = nova.host,nova.instance,nova.zone,aodh,static,cinder.volume,neutron.network,neutron.port,prometheus


Add the http url of Prometheus Alertmanager api for alerts and the receiver name
from the previous step under ``[prometheus]`` section::

    [prometheus]
    alertmanager_url = http://localhost:9093/api/v2/alerts
    receiver = vitrage


Note: Both v1 and v2 Alertmanager apis are supported


Step 3 - Map Prometheus alerts to Vitrage resources
---------------------------------------------------

A configuration file that maps the Prometheus alert labels to a corresponding
Vitrage resource with specific properties (id or other unique properties).
The mapping will most likely be defined by the alert name and other fields.
Set the location of the alerts mapping in ``/etc/vitrage/vitrage.conf``
under ``[prometheus]`` section::

    [prometheus]
    config_file = /path/to/alert/mapping


For example  ::

    [prometheus]
    config_file = /etc/vitrage/prometheus_conf.yaml

Prometheus configuration file structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The configuration file contains a list of ``alerts``. Each alert contains ``key`` and ``resource``.

The ``key`` contains labels which uniquely identify each alert.

The ``resource`` specifies how to identify in Vitrage the resource that the alert is on.
It contains one or more Vitrage property names and corresponding Prometheus alert labels.

For example, for the following Prometheus alert  ::

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


The mapping alerts file looks like this  ::

    alerts:
    - key:
        alertname: HighCpuOnVmAlert
        job: libvirt
      resource:
        instance_name: domain
        host_id: instance


This is an example of alert which generated from libvirt metrics.
The alert is on virtual machine with the libvirt name 'instance-00000004'
running on top of host with the ip '1.1.1.1'.
The alert is identified by its name from ``alertname`` label
and from its ``job`` label. Though the key in the mapping file
contains those two labels and their values.
This alert will be mapped to a resource with following properties ::

    instance_name: "1.1.1.1:9999"
    host_id: "instance-00000004"

