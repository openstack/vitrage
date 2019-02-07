=====================
Vitrage Nova Notifier
=====================

Overview
--------

The main purpose of Vitrage is to provide insights about the state of the
system on problems that are not directly monitored. An example of such
a problem is a switch failure that causes a Nova host to become unreachable,
while Nova is not aware of this problem.

The Nova notifier tries to solve this use case, by calling Nova force-down API
to notify Nova that the host is down.


Configuration
-------------

In order to support this use case, the user should perform the following:

1. Activate the nova notifier. In /etc/vitrage/vitrage.conf:

.. code:: yaml

   [DEFAULT]
   notifiers = nova

2. Determine, in the Vitrage templates, what condition(s) indicates that the
   host is down. For example:

.. code:: yaml

   scenarios:
     - scenario:
       condition: host_down_alarm_on_host
         actions:
           action:
             action_type : mark_down
               action_target:
                 target: host


For more information about the mark-down action, see the Vitrage templates
documentation: templates_

.. _templates: https://docs.openstack.org/vitrage/latest/contributor/vitrage-templates.html
