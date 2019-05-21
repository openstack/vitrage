Kapacitor-Vitrage
=================

Kapacitor will send alert to vitrage by using [ exec-handle ], send to message queue topic of vitrage.
https://docs.influxdata.com/kapacitor/v1.5/working/alerts/


Installation
------------

Copy the 'https://raw.githubusercontent.com/openstack/vitrage/master/vitrage/datasources/kapacitor/auxiliary/kapacitor_vitrage.py' script into the Kapacitor servers.

.. code-block:: bash

  $ cp kapacitor_vitrage.py /etc/kapacitor/kapacitor_vitrage.py
  $ chmod 755 /etc/kapacitor/kapacitor_vitrage.py


Configuration
-------------



1. Define topic , which use for alert publish to. Create file ``forward_to_vitrage.yaml``:


      | topic: forward_to_vitrage
      | id: forward_to_vitrage
      | kind: exec
      | options:
      | prog: '/usr/bin/python'
      | args: ['/etc/kapacitor/kapacitor_vitrage.py','rabbit://<rabbit_user>:<rabbit_pass>@controller']

 **Note:** rabbit://<rabbit_user>:<rabbit_pass>@controller is  Vitrage message bus url,  ``rabbit_user:rabbit_pass`` for devstack rabbitmq is ``stackrabbit/secret``

Run command to define topic

.. code:: bash

    $ kapacitor define-topic-handler ./forward_to_vitrage.yaml

2. Assign your Task to topic, in Tick script define that alert, add in "alert()" step:

      | ...
      | alert()
      | ...
      | .topic('forward_to_vitrage')

In case your Task already in topic and you don't want to add another, you only need to do: append 'exec handler' to TICK script which define it.

      | ...
      | alert()
      | ...
      | .exec('/usr/bin/python', '/etc/kapacitor/kapacitor_vitrage.py', 'rabbit://<rabbit_user>:<rabbit_pass>@controller')

Run command define your task:

.. code::

   $ kapacitor define <task_name> -tick <tick_script>

Vitrage configuration:

1. Add kapacitor to list of datasources in ``/etc/vitrage/vitrage.conf``

.. code::

    [datasources]
    types = kapacitor,zabbix,nova.host,nova.instance,nova.zone,static_physical,aodh,cinder.volume,neutron.network,neutron.port,heat.stack

2. Add section to ``/etc/vitrage/vitrage.conf``

.. code::

    [kapacitor]
    config_file = /etc/vitrage/kapacitor_conf.yaml

3. Create ``/etc/vitrage/kapacitor_conf.yaml`` with this content

.. code ::

    kapacitor:
      - alert:
          host: cloud.compute1    # hostname of host been raised alarm
        vitrage_resource:
          type: nova.host         # resource type of enity vitrage
          name: compute-1         # resource name of enity vitrage
      - alert:
          host: compute-(.*)
        vitrage_resource:
          type: nova.host
          name: ${kapacitor_host}
      - alert:
          host: (.*)
        vitrage_resource:
          type: nova.instance
          name: ${kapacitor_host}

In example:
alarm on host have hostname `cloud.compute1` will map to resource name `compute-1`,

alarm on host have hostname `compute-99` will map to resource name `compute-99`

Another alarm, like alarm on instance will map with resource type ``nova.instance`` and name equal with hostname of instance

4. Restart vitrage service in devstack/openstack

DONE
----

