==============================
Templates Not Operator Support
==============================

Overview
--------

The Templates language supports the "or" and "and" operators at the moment.
Many scenarios can't be described by using only those two operators and thus
we would like to add support for "not" operator as well.

*Note:* This document refers to Vitrage templates version 3.

For previous versions, see:

Version_2_

.. _Version_2: https://docs.openstack.org/vitrage/latest/contributor/not_operator_support_v2.html


Template Structure
==================
The template is written in YAML language, with the following structure.
::

  metadata:
    version: 3
    name: <unique template identifier>
    type: standard
    description: <what this template does>
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


All the sections are in use as described in the "vitrage-templates.rst" file.
But in the condition section it will be possible to write the "not" operator in addition to the "and" and "or" operators.
The "not" operator can be used only before a relationship expression.


Condition Format
----------------
The condition which needs to be met will be phrased using the entities and
relationships previously defined. The condition details are described in the
"vitrage-template-format.rst" and the addition here is the new logical operator "not":

- "not" - indicates that the expression must not be satisfied in order for the
  condition to be met.

The following are examples of valid expressions, where X, Y and Z are
relationships:

- X
- X and Y
- X and Y and Z
- X and not Y
- X and not (Y or Z)
- X and not X


Supported Use Cases
===================

Use Case 1:
-----------
There exists an instance on Host but there is no Alarm on the instance.

 ::

    +--------+         +--------+    Not    +---------+
    |  Host  | ------> |   Vm   | < - - - - |  Alarm  |
    +--------+         +--------+           +---------+

 ::

    metadata:
        version: 3
        name: no_alarm_on_instance_that_contained_in_host
        description: when host contains vm that has no alarm on it, show implications on the host
    entities:
        instance_alarm:
            category: ALARM
            name: instance_mem_performance_problem
        host:
            category: RESOURCE
            type: nova.host
        instance:
            category: RESOURCE
            type: nova.instance
    scenarios:
        - condition: host [contains] instance AND NOT instance_alarm [on] instance
          actions:
               - set_state:
                   state: available
                   target: instance


Use Case 2:
-----------

There exists a host with no alarm.

 ::

    +--------+    Not    +---------+
    |  Host  | < - - - - |  Alarm  |
    +--------+           +---------+

 ::

    metadata:
        version: 3
        name: no_alarm_on_host
        description: when there is no alarm on the host, show implications on the host
    entities:
        host_alarm:
            category: ALARM
            name: host_high_mem_load
        host:
            category: RESOURCE
            type: nova.host
        instance:
            category: RESOURCE
            type: nova.instance
    scenarios:
        - condition:  not instance_alarm [on] instance
          actions:
               - set_state:
                   state: available
                   target: instance


Use Case 3:
-----------

The Switch is attached to a Host that contains a Vm.
The Switch is also comprised to a Network which has a Port.
There is no edge between the Vm and the Port.

::

                   +---------+           +---------+
      +----------- |  Host   | --------> |   Vm    |
      |            +---------+           +---------+
      |                                       |
      v                                       |
 +----------+                                 | N
 |  Switch  |                                 | o
 +----------+                                 | t
      |                                       |
      |                                       |
      |                                       v
      |            +---------+           +---------+
      +----------> | Network | <-------- |  Port   |
                   +---------+           +---------+

 ::

    metadata:
        version: 3
        name: no_connection_between_vm_and_port
        description: when there is no edge between the port and the vm, show implications on the instances
    entities:
        host:
            category: RESOURCE
            type: nova.host
        instance:
            category: RESOURCE
            type: nova.instance
        switch:
            category: RESOURCE
            type: switch
        network:
            category: RESOURCE
            type: neutron.network
        port:
            category: RESOURCE
            type: neutron.port
    scenarios:
        - condition:  host [contains] instance AND switch [connected] host AND switch [has] network AND port [attached] network AND NOT instance [connected] port
          actions:
               - raise_alarm:
                   target: instance
                   alarm_name: instance_mem_performance_problem
                   severity: WARNING


Unsupported Use Cases
=====================

Use Case 1:
-----------

There is a Host contains Vm, which has no edge ("connection") to a stack that has an alarm on it.
Difference: The difference here from the graphs above, is that here there are
two connected component subgraphs (the first is host contains vm, the second is alarm on stack),
and the current mechanism doesn't support such a use case of not operator between many connected component subgraphs.
In the subgraphs above, we had only one vertex which was not connected to the main connected component subgraph.

 ::

    +---------+           +---------+      Not       +---------+            +---------+
    |  Host   | --------> |   Vm    |  - - - - - ->  |  Stack  | <--------- |  Alarm  |
    +---------+           +---------+                +---------+            +---------+

 ::

    metadata:
        version: 3
        name: host_contains_vm_with_no_edge_to_stack_that_has_alarm_on_it
        description: when host contains vm without and edge to a stack that has no alarms, show implications on the instances
    entities:
        host:
            category: RESOURCE
            type: nova.host
        instance:
            category: RESOURCE
            type: nova.instance
        stack:
            category: RESOURCE
            type: heat.stack
        stack_alarm:
            category: ALARM
            name: stack_high_mem_load
    scenarios:
        - condition:  host [contains] instance AND stack_alarm [on] stack AND NOT instance [attached] stack
          actions:
               - set_state:
                   state: available
                   target: instance
