============================
Entity Equivalence Use Cases
============================

Background
==========

There are several use cases that require support for either alarm equivalence
or resource equivalence. The design of these features is in progress, and is
not trivial. The purpose of this document is to define the basic requirements
and use cases that should be supported, regardless of the implementation that
will be selected later on.

The term "equivalence" is used to note resources or alarms that are "equal"
although they are reported by different datasources and some of their
properties might conflict. Alternative terms could be equality, merge,
overlapping, etc.


Basic Equivalence Requirements
==============================

Resource Equivalence
--------------------

We currently have two use cases for resource equivalence.

#. K8s datasource reports VMs that are also reported by Nova
#. Vitrage discovery agent (TBD) reports hosts that are also reported by Nova

Maybe both cases can be solved hard-coded by the datasources themselves. This
option should be checked against the use cases.

Alarm Equivalence
-----------------

We should support the following use cases:

#. Equivalent alarms from different monitors, e.g. Zabbix and Nagios
#. Non-equivalent alarms from different monitors, e.g. Zabbix and Nagios
   (meaning the alarms are similar but not the same)
#. Equivalence between a monitored alarm and a Vitrage deduced alarm

Equivalence Definition
----------------------

In order to support these use cases, we **must** define a way for the user to
determine which entities are equivalent.

For resources we should define:

* Which properties determine the equivalence. E.g. Nova instance UUID equals
  k8s vm externalID
* Optional: what property should be used in case of conflict (could it be done
  arbitrarily or hard-coded?)

For alarms we should define:

* Which properties determine the equivalence. E.g. Zabbix ALARM name "HIGH CPU"
  equals Prometheus alarm name "high cpu".
* Hidden assumption: equivalent alarms are always "on" the same resource.

Equivalence should be transitive. If the user defines two equivalences with a
common entity, then all entities should be equivalent to one another.

For Example:

* Zabbix high_cpu ~ Nagios HIGH_CPU
* Nagios HIGH_CPU ~ Prometheus High CPU

Vitrage will handle Zabbix, Nagios and Prometheus CPU alarms as all equivalent
to one another.

**Note**: We must support both hard-coded and user-defined equivalence
definitions.

* Hard-coded equivalence: k8s vms always map to Nova vms by the same strategy.
  We can't let the user change it.
* User-defined equivalence: the end user may decide that two alarms are, or are
  not, equivalent. The user should be able to change this definition at any
  time. The equivalence definition should be tenant-specific (see the section
  about multi tenancy).

Merge Strategy
--------------

There are different approaches for what information the user should see in case
there is a conflict between two datasources. The user should be able to define
the wanted "merge strategy" out of the following options:

#. last_update: Use the properties from the last update.
#. most_credible: Use the properties from the most credible datasource.
   A 'credibility' property should be added to each datasource. By default,
   most datasources will have 'medium' credibility, except from Vitrage that
   will have 'low' credibility. The user will be able to change it in
   vitrage.conf options.
   If the equivalent datasources have the same credibility, last_update merge
   strategy will be used.
#. worst_state: In case of state/severity calculation: Use the worst state of
   all.

The default, which is the current behavior, will be worst_state.

Equivalence Use Cases
=====================

1. Two datasources report the same resource
-------------------------------------------

1.1. Nova reports first, then Vitrage discovery agent
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Nova host datasource asks to create nova.host entity
#. Vitrage discovery agent datasource asks to create host (nova.host?) entity

Expected behavior: Vitrage API returns a single host

1.2. Vitrage discovery agent reports first
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Similar to 1.a, but the discovery agent reports first

1.3. Nova reports again on the next get_all
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. An entity in the graph already exists for the host, with properties from
   both datasources
#. Nova host datasources reports the same host again

Expected behavior: There should be no change in what the API returns

1.4. Conflict in the host state
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Nova host datasource asks to create nova.host entity with state ERROR
#. Vitrage discovery agent datasource asks to create host entity with state
   ACTIVE

Expected behavior: Vitrage API returns a single host with a state that depends
on the merge strategy.

+----------------+------------------+
| Merge Strategy | Aggregated state |
+================+==================+
| last_update    | ACTIVE           |
+----------------+------------------+
| most_credible  | ERROR            |
+----------------+------------------+
| worst_state    | ERROR            |
+----------------+------------------+

1.5. Nova and K8s have different vm names
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Nova instance datasource asks to create nova.instance entity named 'vm1'
#. K8s datasource asks to create instance entity named 'VM_1'

Both vms are equivalent by the Nova UUID.

Expected behavior: Vitrage API will return a single instance. Its name will
be determined by one of the datasources in a consistent way (meaning it will
be either always the K8s name or always the Nova name).

1.6. One datasource stops reporting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Nova host datasource asks to create nova.host entity
#. Vitrage discovery agent datasource asks to create host (nova.host?) entity
#. ...
#. Vitrage discovery agent crashes and stops reporting
#. In the next get_all, Vitrage discovery agent reports nothing

Expected behavior:

* The host is not deleted
* The data that was provided by Nova is returned

2. Two monitors report the same alarm (e.g. Zabbix and Prometheus)
------------------------------------------------------------------

2.1. Zabbix reports CRITICAL, Nagios reports WARNING
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Zabbix datasource asks to create a Zabbix alarm with severity CRITICAL
#. Nagios datasource asks to create a Nagios alarm with severity WARNING

Expected behavior: Vitrage API returns a single alarm with a severity that
depends on the merge strategy.

+----------------+---------------------+
| Merge Strategy | Aggregated severity |
+================+=====================+
| last_update    | WARNING             |
+----------------+---------------------+
| most_credible  | CRITICAL            |
+----------------+---------------------+
| worst_state    | CRITICAL            |
+----------------+---------------------+

2.2. Zabbix reports CRITICAL, Nagios reports WARNING, Zabbix reports OK
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Nagios datasource asks to create a Nagios alarm with severity WARNING
#. Zabbix datasource asks to create a Zabbix alarm with severity CRITICAL
#. Zabbix datasource changes the severity to OK


Expected behavior: depends on the merge strategy.

+----------------+---------------------------+
| Merge Strategy | Aggregated severity       |
+================+===========================+
| last_update    | OK (the alarm is deleted) |
+----------------+---------------------------+
| most_credible  | WARNING                   |
+----------------+---------------------------+
| worst_state    | WARNING                   |
+----------------+---------------------------+

2.3. Zabbix, Nagios and Prometheus report the same alarm
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Assume that the merge strategy is worst_state.

#. Prometheus datasource asks to create Prometheus alarm with severity WARNING
#. Zabbix datasource asks to create a Zabbix alarm with severity CRITICAL
#. Nagios datasource asks to create a Nagios alarm with severity CRITICAL

Expected behavior: Vitrage API returns a single alarm with severity CRITICAL

3. Two monitors report similar yet different alarms
---------------------------------------------------

#. Nagios datasource asks to create a Nagios "high CPU" alarm
#. Zabbix datasource asks to create a Zabbix "extremely high CPU" alarm

Expected behavior: Vitrage API returns two alarms

4. A monitor reports the same alarm as a Vitrage deduced alarm
--------------------------------------------------------------

This use case is detailed also in https://review.openstack.org/#/c/547931/

4.1. Nagios reports first
^^^^^^^^^^^^^^^^^^^^^^^^^

#. Nagios datasource asks to create a Nagios alarm with severity WARNING
#. Vitrage evaluator asks to create a deduced alarm with severity CRITICAL

Expected behavior: Vitrage API returns a single alarm with severity that
depends on the merge strategy.

+----------------+---------------------+
| Merge Strategy | Aggregated severity |
+================+=====================+
| last_update    | CRITICAL            |
+----------------+---------------------+
| most_credible  | WARNING             |
+----------------+---------------------+
| worst_state    | CRITICAL            |
+----------------+---------------------+

4.2. Nagios reports alarm, Vitrage deduced alarm, Nagios reports OK
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Nagios datasource asks to create a Nagios alarm
#. Vitrage evaluator asks to create a deduced alarm with severity WARNING
#. Nagios datasource asks to delete the Nagios alarm

Expected behavior: depends on the merge strategy.

+----------------+---------------------------+
| Merge Strategy | Aggregated severity       |
+================+===========================+
| last_update    | OK (the alarm is deleted) |
+----------------+---------------------------+
| most_credible  | OK (the alarm is deleted) |
+----------------+---------------------------+
| worst_state    | WARNING                   |
+----------------+---------------------------+

The behavior for worst_state strategy:

* The alarm is not deleted (Vitrage still identifies a problem, let's not
  ignore it)
* The alarm contains all Vitrage properties
* A diagnose action is executed, if such an action is defined


4.3. Nagios, Zabbix and Vitrage report an alarm
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Nagios datasource asks to create a Nagios alarm with severity WARNING
#. Vitrage evaluator asks to create a deduced alarm with severity CRITICAL
#. Zabbix datasource asks to create a Zabbix alarm with severity WARNING

Expected behavior: Vitrage API returns a single alarm with properties from
Nagios, Zabbix and Vitrage and severity that depends on the merge strategy.

+----------------+---------------------+
| Merge Strategy | Aggregated severity |
+================+=====================+
| last_update    | WARNING             |
+----------------+---------------------+
| most_credible  | WARNING             |
+----------------+---------------------+
| worst_state    | CRITICAL            |
+----------------+---------------------+

5. The user changes the alarm equivalence definition
----------------------------------------------------

5.1. Nagios, Zabbix and Vitrage are equivalent, then the user changes it
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Assume that the merge strategy is last_update.

#. Vitrage datasource asks to create a Zabbix alarm with severity WARNING
#. Zabbix datasource asks to create a Zabbix alarm with severity WARNING
#. Nagios datasource asks to create a Nagios alarm with severity CRITICAL
#. Vitrage API returns a single alarm with severity CRITICAL
#. The user changes the equivalence definition so Vitrage and Zabbix are
   equivalent to each other but Nagios is not equivalent to them

Expected behavior: Vitrage API returns two alarms:

* Zabbix+Vitrage alarm with severity WARNING
* Nagios alarm with severity CRITICAL

**Note:** Since in Rocky we are going to implement vitrage-graph start-up from
the database, there is no real difference if the user restarts the graph after
he changes the equivalence definition or not.

5.2. Zabbix and Vitrage are equivalent, then the makes Nagios equivalent too
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Assume that the merge strategy is last_update.

#. Vitrage datasource asks to create a Zabbix alarm with severity WARNING
#. Zabbix datasource asks to create a Zabbix alarm with severity WARNING
#. Nagios datasource asks to create a Nagios alarm with severity CRITICAL
#. Vitrage API returns two alarms:

   * Zabbix+Vitrage alarm with severity WARNING
   * Nagios alarm with severity CRITICAL
#. The user changes the equivalence definition so Vitrage, Zabbix and Nagios
   are equivalent to each other

Expected behavior: Vitrage API returns a single alarm with severity CRITICAL

6. Template on one datasource should apply to another datasource
----------------------------------------------------------------

6.1. Simple alarm equivalence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Assume that Zabbix high_cpu alarm is equivalent to Nagios HIGH_CPU alarm.


Template example:

 ::

  definitions:
   entities:
    - entity:
       category: ALARM
       rawtext: high_cpu
       type: zabbix
       template_id: zabbix_alarm

  scenarios:
   - scenario:
      condition: zabbix_alarm_on_host
      actions:
       - ...



#. Nagios datasource asks to create a Nagios HIGH_CPU alarm
#. Zabbix datasource DOES NOT ask to create a Zabbix high_cpu alarm (yet)

Expected behavior: the actions in the scenario are executed as a result of the
Nagios alarm.


6.2. Simple resource equivalence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Assume that Nova host is equivalent to Vitrage discovery agent host.


Template example:

 ::

  definitions:
   entities:
    - entity:
       category: RESOURCE
       type: nova.host
       template_id: nova_host
    - entity:
       category: RESOURCE
       type: discovery_host (???)
       template_id: discovery_host

  scenarios:
   - scenario:
      condition: discovery_host and discovery_host_contains_instance
      actions:
       - ...


Expected behavior: the scenario will work if the host contains an instance, no
matter if the host is defined by Nova or by Vitrage discovery agent.


6.3. alarm equivalence + resource equivalence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Assume that Zabbix high_cpu alarm is equivalent to Nagios HIGH_CPU alarm
**and** Nova host is equivalent to Vitrage discovery agent host.


Template example:

 ::

  scenarios:
   - scenario:
      condition: discovery_host and discovery_host_contains_instance and
                 zabbix_alarm_on_discovery_host
      actions:
       - ...


Expected behavior: the scenario will work if the host contains an instance, no
matter if the host is defined by Nova or by Vitrage discovery agent; and if
either Zabbix alarm of Nagios alarm was raised on the host.


7. Template on one datasource should **not** apply to another datasource
------------------------------------------------------------------------

Assume that Zabbix high_cpu alarm is equivalent to Nagios HIGH_CPU alarm.

Template example:

 ::

  definitions:
   entities:
    - entity:
       category: ALARM
       rawtext: high_cpu
       type: zabbix
       severity:warning
       template_id: zabbix_alarm
    - entity:
       category: ALARM
       name: HIGH_CPU
       type: nagios
       template_id: nagios_alarm

  scenarios:
   - scenario:
      condition: zabbix_alarm_on_host
      actions:
       - ...

This use case is the same as 5.1, with one exception: the template entity
zabbix_alarm is defined only for the case that the severity is warning. What
will happen if a Nagios alarm is raised with severity warning? and what if it
is raised with a different severity?

8. Overlapping templates
------------------------

Is the overlapping templates mechanism somehow related to the equivalence use
cases?

9. Multi Tenancy
----------------

Per-tenant equivalence
^^^^^^^^^^^^^^^^^^^^^^

Entity equivalence should be defined for a specific tenant. One tenant may want
to see Nagios and Zabbix alarms as one alarm, while the other tenant may want
to see them separated.

Cross-tenant equivalence
^^^^^^^^^^^^^^^^^^^^^^^^

Is it possible that equivalent resources will be reported on different tenants?

#. Nova instance datasource asks to create nova.instance for tenant_1
#. k8s datasource asks to create instance (nova.instance?) with the same UUID
   for tenant_2

What do we do in such a case?
