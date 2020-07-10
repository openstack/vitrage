===============
Using Templates
===============

Overview
########
In Vitrage we use configuration files, called ``templates``, to express rules
regarding raising deduced alarms, setting deduced states, and detecting/setting
RCA links.
This page describes the format of the Vitrage templates, with some examples.
Additionally, a short guide on adding templates is presented.

*Note:* This document refers to Vitrage templates version 3.

For previous versions, see:

Version_1_

Version_2_

.. _Version_1: https://docs.openstack.org/vitrage/pike/
.. _Version_2: https://docs.openstack.org/vitrage/latest/contributor/vitrage-template-format-v2.html


Template Structure
##################
The template is written in YAML language, with the following structure:

.. code-block:: yaml

   metadata:
    version: 3
    name: <unique template identifier>
    type: standard
    description: <what this template does>
   parameters: <an optional section>
    example_param:
     description: <description of the parameter>
     default: <a default value for the parameter>
   entities:
    example_host:
     type: nova.host
     name: compute-0-0
    example_instance:
     type: nova.instance
    example_alarm:
     type: zabbix
     name: memory threshold crossed
   scenarios:
    - condition: <if statement true do the actions>
      actions:
        ...

The template is divided into three main sections:

- ``metadata`` - contains general information about the template.

  - ``version`` - the version of the template format.
  - ``name`` - the name of the template
  - ``type`` - the type of the template. Currently only `standard` is supported
  - ``description`` - a brief description of what the template does (optional)

- ``parameters`` - an optional section with parameters that are used inside the template

- ``entities`` - describes the resources and alarms which are relevant to the template scenario (corresponds to a vertex in the entity graph). These are referenced later on.

- ``scenarios`` - a list of if-then scenarios to consider. Each scenario is comprised of:

  - ``condition`` - an expression describing the existence of a structure in the topology
  - ``actions`` - a list of actions to execute when the condition is met.


Scenario Condition
==================

The condition expression is evaluated to True or False depending on the existence of such a structure in the entity graph.
An expression is either a *single* entity, a declaration describing a relationship between two entities, or some logical combination of these.

Example 1
---------

.. code-block:: yaml

   scenarios:
    - condition: example_host
      actions:

True if an entity exists with properties matching those defined in `example_host`, False otherwise

Example 2
---------

.. code-block:: yaml

   scenarios:
    - condition: example_host [ contains ] example_instance
      actions:

True if all of the following are True:
 - An entity exists with properties matching those defined in `example_host`
 - An entity exists with properties matching those defined in `example_instance`
 - Between these two entities, exists a relationship (graph edge) with a label `contains`

Logical Operators
-----------------

Expressions can be combined using the following logical operators:

- `AND` - Both expressions must be satisfied.
- `OR` - At least one expression must be satisfied (non-exclusive or).
- `NOT` - The expression must not be satisfied in order for the condition to be met.
- `()` - parentheses clause indicating the scope of an expression.


Example 3
---------

.. code-block:: yaml

   scenarios:
    - condition: example_host [ contains ] example_instance AND example_alarm [ on ] example_host
      actions:

True if all of the following are True:
 - An entity exists with properties matching those defined in `example_host`
 - An entity exists with properties matching those defined in `example_instance`
 - An entity exists with properties matching those defined in `example_alarm`
 - Between `host` and `instance`, exists a relationship (graph edge) with a label `contains`
 - Between `alarm` and `host`, exists a relationship (graph edge) with a label `on`

Example 4
---------

.. code-block:: yaml

    - condition: example_host [ contains ] example_instance AND NOT example_alarm [ on ] example_host
      actions:

Similar to the example 3, adding the `NOT` means there must not exist an edge with `on` label, between `alarm` and `host`.

Further examples
----------------

A few more example conditions:

- `entity_a [contains] entity_b`
- `entity_a [contains] entity_b AND entity_b [contains] entity_c AND entity_c [contains] entity_d`
- `entity_a [contains] entity_b AND NOT entity_a [contains] entity_c`
- `entity_a [contains] entity_b AND NOT (entity_a [contains] entity_c OR entity_a [contains] entity_d)`

A few restrictions regarding the condition format
-------------------------------------------------

A condition can not be entirely "negative", it must have at least one part that does not have a `NOT` in front of it. This example is illegal:

::

 This condition is illegal:
 condition: NOT example_alarm [on] example_instance

 Instead, add a positive term:
 condition: example_instance AND NOT example_alarm [on] example_instance

There must be at least one entity that is common to all `OR` clauses.

::

 This condition is illegal:
 example_alarm_1 [on] example_instance OR example_alarm_2 [on] example_host

 Instead, use two separate conditions and scenarios.

For more information, see the 'Calculate the action_target' section in external actions Spec_.

.. _Spec: https://specs.openstack.org/openstack/vitrage-specs/specs/pike/external-actions.html

Scenario Actions
================

Each scenario contains `condition` and `actions`. When the `condition` is met, all the scenario's
actions are executed. The executed actions may be reverted if the condition is no longer met.

All supported actions described below, use the following entities definitions:

.. code-block:: yaml

    metadata:
        version: 3
        name: Entities for action examples
        type: standard
    entities:
        - host:
            type: nova.host
        - host_alarm:
            category: ALARM
        - instance:
            type: nova.instance
        - instance_alarm:
            category: ALARM

Set State
---------

.. code-block:: yaml

 - condition: host_alarm [on] host
   actions:
     - set_state:
        state: ERROR                         # Mandatory - ERROR/SUBOPTIMAL/OK
        target: host                         # Mandatory - Entity key

This action will change the state of the `target` resource to the specified `state`.
Affect the state seen in Vitrage.
Once the condition is no longer met, the state will reverted to the result of either the data source state, or any other scenario.

Raise Alarm
-----------

.. code-block:: yaml

 - condition: host_alarm [on] host AND host [contains] instance
   actions:
    - raise_alarm:
       target: instance                      # Mandatory - Entity key
       alarm_name: affected by host problem  # Mandatory - Any string
       severity: WARNING                     # Mandatory - CRITICAL/WARNING
       causing_alarm: host_alarm             # Optional - Entity key

This action creates a new alarm vertex, with the specified `alarm_name` as its `name` property.
This alarm vertex will have an edge to the `target` vertex, with a label `on`.
Optionally, if `causing_alarm` is specified, another edge will be added, from the `causing_alarm` vertex to the new alarm vertex, with a label `causes`.
Notice: `on` and `causes` edge labels, are predefined values.
Once the condition is no longer met, the alarm may be removed, if it is not the result of any other scenario.

Add Causal Relationship
-----------------------

.. code-block:: yaml

 - condition: host_alarm [on] host AND host [contains] instance AND instance_alarm [on] instance
   actions:
     - add_causal_relationship:
        source: host_alarm
        target: instance_alarm

A new edge will be added, from the `source` vertex to the `target` vertex, with a label `causes`.
Once the condition is no longer met, the edge may be removed, if it is not the result of any other scenario.
Notice: `causes` edge label, is a predefined value.

Mark Down
---------

.. code-block:: yaml

 - condition: host_alarm [on] host
   actions:
     - mark_down:
        target: host                         # Mandatory - Entity key

Set an entity's `marked_down` field.
This action will add a `marked_down` property to the resource (Supported by nova notifier).
This can be used along with nova notifier to:
- call nova force_down for a host.
- call nova reset-server-state for an instance.
Once the condition is no longer met, the `marked_down` property may be removed, if it is not the result of any other scenario.

Execute Mistral
---------------

.. code-block:: yaml

 - condition: host_alarm [on] host
   actions:
     - execute_mistral:
        workflow: work_1                      # Mandatory - Workflow name
        input:                                # Optional - Dictionary of custom workflow input
          some_property: 5
          another_property: hello

Execute a Mistral workflow.
If the Mistral notifier is used, the specified workflow will be executed with
its parameters.

Advanced
========

Regular expressions
-------------------
All parameters within an entity definition can be made to include regular
expressions. To do this, simply add `.regex` to their key. For example, as
Zabbix supports regular expressions and a Zabbix alarm contains a `rawtext`
field which is a regular expression, a Zabbix alarm entity defined in the
template may contain a ``rawtext.regex`` field that is also defined by a
regular expression:
::

  - zabbix_alarm:
     category: ALARM
     type: zabbix
     rawtext.regex: Interface ([_a-zA-Z0-9'-]+) down on {HOST.NAME}


Parameters
----------
Some properties in the template definition can be defined as parameters and
assigned with actual values upon template creation. This allows easy reuse of
a similar template structure for different alarm types.

For example, the following two templates can be written using a single template
with parameters:

* a high CPU load on a host causes high CPU load on the instances
* insufficient memory on a host causes insufficient memory on the instances

To use parameters, add a ``parameters`` section to the template. This section
defines all parameters that are used in the template. Each parameter can have
two optional properties:

* ``description``: explanation on the purpose of the parameter
* ``default``: default value for the parameter

Using a parameter inside the template is done by calling the ``get_param()``
function. For example:

::

    name: get_param(alarm_name)

**Note:** In order to be able to create multiple templates from the
parametrized template, the template name must also be defined as a parameter.


Functions
---------
Some properties of an action can be defined using functions. On version 2, one
function is supported: `get_attr`, and it is supported only for `execute_mistral`
action.


get_attr
^^^^^^^^
This function retrieves the value of an attribute of an entity that is defined
in the template.

::

    get_attr(template_id, attr_name)

.. code-block:: yaml

    metadata:
        ...
    entities:
        - host:
            type: nova.host
        - host_alarm:
            type: zabbix
            name: host connectivity problem
    scenarios:
     - condition: host_alarm [on] host
       actions:
         - execute_mistral:
            workflow: demo_workflow
            input:
              host_name: get_attr(host, name)
              retries: 5

get_param
^^^^^^^^^
See `Parameters`_


Examples
########


Example 1: Basic RCA and Deduced Alarm/State
============================================
The following template demonstrates:

1. How to raise a deduced alarm. Specifically, if there is high CPU load on a
   host, raise alarm indicating CPU performance problems on all contained
   instances.
2. How to link alarms for purposes of root cause analysis (RCA). Specifically,
   if there is high CPU load on the host and CPU performance problems on the
   hosted instances, we link them with a `causes` relationship, according to
   the optional property `causing_alarm`.

.. code-block:: yaml

    metadata:
        version: 3
        name: EXAMPLE 1 - host high CPU load to instance CPU suboptimal
        type: standard
        description: when there is high CPU load on the host, show implications on the instances
    entities:
        host:
          type: nova.host
        host_alarm:
          type: zabbix
          name: host high cpu load
        instance:
          type: nova.instance
        instance_alarm:
          category: ALARM
          severity: CRITICAL
    scenarios:
     - condition: host_alarm [on] host AND host [contains] instance
       actions:
         - raise_alarm:
            target: instance
            alarm_name: instance cpu performance problem
            severity: WARNING
            causing_alarm: host_alarm
     - condition: instance_alarm [on] instance
       actions:
         - set_state:
            state: SUBOPTIMAL
            target: instance


Example 2: Deduced state based on alarm
=======================================
The following template will change the state of an instance to `ERROR` if there
is any alarm of severity `CRITICAL` on it.

.. code-block:: yaml

    metadata:
        version: 3
        name: EXAMPLE 3 - deduced state for instances with critical alarm
        type: standard
        description: deduced state for all instance with alarms
    entities:
        instance:
          type: nova.instance
        instance_alarm:
          category: ALARM
          severity: CRITICAL
    scenarios:
     - condition: instance_alarm [on] instance
       actions:
         - set_state:
            state: ERROR
            target: instance

Example 3: Deduced alarm based on state
=======================================
This template will cause an alarm to be raised on any host in state `ERROR`

Note that in this template, there are no relationships. The condition is just
that the entity exists.


.. code-block:: yaml

    metadata:
        version: 3
        name: EXAMPLE 3 - deduced alarm for all hosts in error
        type: standard
        description: raise deduced alarm for all hosts in error
    entities:
        host_in_error:
          type: nova.host
          state: error
    scenarios:
     - condition: host_in_error
       actions:
         - raise_alarm:
            target: host_in_error
            alarm_name: host in error state
            severity: CRITICAL

Example 4: Deduced Alarm triggered by several options
=====================================================
This template will raise a deduced alarm on an instance, which can be caused by
an alarm on the hosting zone or an alarm on the hosting host.


.. code-block:: yaml

    metadata:
        version: 3
        name: EXAMPLE 4 - deduced alarm two possible triggers
        type: standard
        description: deduced alarm using or in condition
    entities:
        zone:
          type: nova.zone
        zone_alarm:
          category: ALARM
          name: zone connectivity problem
        host:
          type: nova.host
        host_alarm:
          type: zabbix
          name: host connectivity problem
        instance:
          type: nova.instance
    scenarios:
     - condition: (host_alarm [on] host OR (zone_alarm [on] zone AND zone [contains] host)) AND host [contains] instance
       actions:
         - raise_alarm:
            target: instance
            alarm_name: instance_connectivity_problem
            severity: CRITICAL


Example 5: A template with parameters
=====================================
This template will raise a deduced alarm on an instance if there is an alarm
on the host.


.. code-block:: yaml

    metadata:
        version: 3
        name: get_param(template_name)
        type: standard
        description: If there is an alarm on a host, raise alarms on its instances
    parameters:
        template_name:
        host_alarm_type:
           description: the type of the alarm on the host
           default: zabbix
        host_alarm_name:
           description: the name of the alarm on the host
        instance_alarm_name:
           description: the name of the alarm on to be raised by Vitrage on the instance
        instance_alarm_severity:
           description: the severity of the alarm on to be raised by Vitrage on the instance
           default: WARNING
    entities:
        zone:
            type: nova.zone
        host:
            type: nova.host
        host_alarm:
            type: get_param(host_alarm_type)
            name: get_param(host_alarm_name)
        instance:
            type: nova.instance
    scenarios:
     - condition: host_alarm [on] host AND host [contains] instance
       actions:
         - raise_alarm:
            target: instance
            alarm_name: get_param(instance_alarm_name)
            severity: get_param(instance_alarm_severity)


`vitrage template add` should be called with the following parameters:

* template_name
* host_alarm_type (optional)
* host_alarm_name
* instance_alarm_name
* instance_alarm_severity (optional)

::

  vitrage template add --path template_with_params.yaml --params template_name=cpu_template host_alarm_name='High CPU on host' instance_alarm_name='CPU performance degradation on the instance'


Applying the template
#####################


Template Validate
=================
Before adding a template you can validate it

::

    vitrage template validate --path /home/stack/my_new_template.yaml

Template Add
============
Applying the template will evaluate it against the existing entity graph as well as to any new data.

::

    vitrage template add --path /home/stack/my_new_template.yaml


Common properties and their acceptable values
=============================================

+-------------------+-----------------------+-------------------------+------------------------------------+
| block             | key                   | supported values        | comments                           |
+===================+=======================+=========================+====================================+
| entity            | category              | ALARM,                  |                                    |
|                   |                       | RESOURCE                |                                    |
+-------------------+-----------------------+-------------------------+------------------------------------+
| entity (ALARM)    | type                  | vitrage,                |                                    |
|                   |                       | zabbix,                 |                                    |
|                   |                       | doctor,                 |                                    |
|                   |                       | aodh,                   |                                    |
|                   |                       | prometheus,             |                                    |
|                   |                       | nagios,                 |                                    |
+-------------------+-----------------------+-------------------------+------------------------------------+
| entity (RESOURCE) | type                  | openstack.cluster,      | These are for the datasources that |
|                   |                       | nova.zone,              | come with vitrage by default.      |
|                   |                       | nova.host,              | Adding datasources will add more   |
|                   |                       | nova.instance,          | supported types, as defined in the |
|                   |                       | cinder.volume,          | datasource transformer             |
|                   |                       | switch                  |                                    |
+-------------------+-----------------------+-------------------------+------------------------------------+
| actions           |                       | raise_alarm,            |                                    |
|                   |                       | set_state,              |                                    |
|                   |                       | add_causal_relationship,|                                    |
|                   |                       | mark_down,              |                                    |
|                   |                       | execute_mistral         |                                    |
+-------------------+-----------------------+-------------------------+------------------------------------+
