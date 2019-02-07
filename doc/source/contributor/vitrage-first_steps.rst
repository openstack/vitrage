===============================
Vitrage - Getting Started Guide
===============================

This document explains how to get started using Vitrage. Here you will find
easy-to-follow instructions on how to install & configure Vitrage to suit
your needs, try out its different functions, and expand it's capabilities.

Before you start
================

Installation
============
- `Enable Vitrage in devstack <https://github.com/openstack/vitrage/blob/master/devstack/README.rst>`_
- `Enable Vitrage in horizon <https://github.com/openstack/vitrage-dashboard/blob/master/README.rst>`_
- run ``./stack.sh``


Nagios Installation & Configuration
===================================
Nagios_ is a widely-used tool for monitoring hardware and software systems.
It periodically runs tests on the entities it monitors, and sets the state
of these tests to OK (pass) or different levels of severity.

Vitrage comes with Nagios as a datasource, The examples given below use Nagios
as the trigger for deduced alarms, states and RCA templates in Vitrage.

.. _Nagios: https://www.nagios.org/

- `Install Nagios on your devstack <https://docs.openstack.org/vitrage/latest/contributor/nagios-devstack-installation.html>`_
- `Configure Nagios datasource <https://docs.openstack.org/vitrage/latest/contributor/nagios-config.html>`_


Vitrage in action
=================

In order to see Vitrage in action, you should add templates to Vitrage using
``vitrage template add`` API. See template_ example.

.. _template: host_high_memory_consumption.yaml

In the example shown here, we will cause Nagios to report high memory usage on
the devstack host. As a result and as defined in our sample template, Vitrage
will change the state of the hosted instances to "suboptimal", raise an alarm
on each and  indicate that the host-level alarm is the cause for the instance
alarms.

Setting up
----------
- Deploy several (3-5) instances on your devstack. Make sure that they are
  in state "Running" before continuing.
- In your browser, go to the Nagios site you defined. If you used the
  steps defined above:

  - URL: *http://<IP>:54321/my_site/omd/*
  - Select "Classic Nagios GUI" (other views are ok as well, the instructions
    below on raising alarms are for this view). If you do not see "Classic Nagios GUI", please do as following:

    .. code:: bash

      su - my_site
      omd config
      # Change GUI to Nagios
      # Restart my_site
      omd restart

  - User/Password: omdadmin/omd
- Set the "Memory Used" test to "Warning":

  - Click on *Services --> Memory Used*
  - On the right pane, select "Submit passive check result for this service"
  - For the "Check result" enter "Warning"
  - For "Check Output" enter "High memory usage". Click *commit*, then *Done*.
  - On the right pane, select "Stop accepting passive checks for this service"
    and then *Done*.

With the alarm on the host now activated, lets see how this is expressed in
Vitrage.


Deduced State
-------------

- In the Horizon UI, select *Vitrage --> Topology*
- The UI will now show the Sunburst view of the compute hierarchy. The color
  of each resource reflects its state: green (ok), yellow (warning), red
  (critical).

  A list of alarms will appear in the UI, showing an alarm on the host, as well
  as one alarm per instance.


Deduced Alarm
-------------

- In the Horizon UI, select *Vitrage --> Alarms*
- A list of alarms will appear in the UI, showing an alarm on the host, as well
  as one alarm per instance.


Root Cause Analysis
-------------------
- In the Horizon UI, select *Vitrage --> Alarms*
- Select a host alarm, and click on the RCA icon in the far right-hand side of
  the screen. This will show how the host alarm caused the instance alarms

Advanced Usage
==============

Modify states & severities
--------------------------
Since each data-source might represent a resource state or alarm severity
differently, for each data-source you can define it's own mapping to the
*normalized* states/severities supported in Vitrage. This will impact UI and
templates behavior that depends on these fields.

- `Resource state configuration <https://docs.openstack.org/vitrage/latest/contributor/resource-state-config.html>`_
- `Alarm severity configuration <https://docs.openstack.org/vitrage/latest/contributor/alarm-severity-config.html>`_

Writing your own templates
--------------------------
For more information regarding Vitrage templates, their format and how to add
them, see here_.

.. _here: https://docs.openstack.org/vitrage/latest/contributor/vitrage-templates.html
