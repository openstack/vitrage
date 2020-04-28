==========================================
Templates Not Operator Support - Version 2
==========================================

Overview
--------

The Templates language supports the "or" and "and" operators at the moment.
Many scenarios can't be described by using only those two operators and thus
we would like to add support for "not" operator as well.


Template Structure
==================
The template is written in YAML language, with the following structure.
::

  metadata:
    version: <template version>
    name: <unique template identifier>
    description: <what this template does>
  definitions:
    entities:
        - entity: ...
        - entity: ...
    relationships:
        - relationship: ...
        - relationship: ...
  scenarios:
      - scenario:
          condition: <if statement true do the action>
          actions:
              - action: ...


All the sections are in use as described in the "vitrage-template-format.rst" file.
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
        version: 2
        name: no_alarm_on_instance_that_contained_in_host
        description: when host contains vm that has no alarm on it, show implications on the host
    definitions:
        entities:
            - entity:
                category: ALARM
                name: instance_mem_performance_problem
                template_id: instance_alarm # some string
            - entity:
                category: RESOURCE
                type: nova.host
                template_id: host
            - entity:
                category: RESOURCE
                type: nova.instance
                template_id: instance
        relationships:
            - relationship:
                source: instance_alarm
                target: instance
                relationship_type: on
                template_id : alarm_on_instance
            - relationship:
                source: host
                target: instance
                relationship_type: contains
                template_id : host_contains_instance
    scenarios:
        - scenario:
            condition: host_contains_instance and not alarm_on_instance
            actions:
                - action:
                   action_type: set_state
                   properties:
                      state: available
                   action_target:
                      target: host


Use Case 2:
-----------

There exists a host with no alarm.

 ::

    +--------+    Not    +---------+
    |  Host  | < - - - - |  Alarm  |
    +--------+           +---------+

 ::

    metadata:
        version: 2
        name: no_alarm_on_host
        description: when there is no alarm on the host, show implications on the host
    definitions:
        entities:
            - entity:
                category: ALARM
                name: host_high_mem_load
                template_id: host_alarm # some string
            - entity:
                category: RESOURCE
                type: nova.host
                template_id: host
            - entity:
                category: RESOURCE
                type: nova.instance
                template_id: instance
        relationships:
            - relationship:
                source: host_alarm  # source and target from entities section
                target: host
                relationship_type: on
                template_id : alarm_on_host
    scenarios:
        - scenario:
            condition: not alarm_on_host
            actions:
                - action:
                   action_type: set_state
                   properties:
                      state: available
                   action_target:
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
        version: 2
        name: no_connection_between_vm_and_port
        description: when there is no edge between the port and the vm, show implications on the instances
    definitions:
        entities:
            - entity:
                category: RESOURCE
                type: nova.host
                template_id: host
            - entity:
                category: RESOURCE
                type: nova.instance
                template_id: instance
            - entity:
                category: RESOURCE
                type: switch
                template_id: switch
            - entity:
                category: RESOURCE
                type: neutron.network
                template_id: network
            - entity:
                category: RESOURCE
                type: neutron.port
                template_id: port
        relationships:
            - relationship:
                source: host
                target: instance
                relationship_type: contains
                template_id : host_contains_instance
            - relationship:
                source: switch
                target: host
                relationship_type: connected
                template_id : host_connected_switch
            - relationship:
                source: switch
                target: network
                relationship_type: has
                template_id : switch_has_network
            - relationship:
                source: port
                target: network
                relationship_type: attached
                template_id : port_attached_network
            - relationship:
                source: instance
                target: port
                relationship_type: connected
                template_id : vm_connected_port
    scenarios:
        - scenario:
            condition: host_contains_instance and host_connected_switch and switch_has_network and port_attached_network and not vm_connected_port
            actions:
                - action:
                   action_type: raise_alarm
                   properties:
                      alarm_name: instance_mem_performance_problem
                      severity: warning
                   action_target:
                      target: instance



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
        version: 2
        name: host_contains_vm_with_no_edge_to_stack_that_has_alarm_on_it
        description: when host contains vm without and edge to a stack that has no alarms, show implications on the instances
    definitions:
        entities:
            - entity:
                category: RESOURCE
                type: nova.host
                template_id: host
            - entity:
                category: RESOURCE
                type: nova.instance
                template_id: instance
            - entity:
                category: RESOURCE
                type: heat.stack
                template_id: stack
            - entity:
                category: ALARM
                name: stack_high_mem_load
                template_id: stack_alarm
        relationships:
            - relationship:
                source: host
                target: instance
                relationship_type: contains
                template_id : host_contains_instance
            - relationship:
                source: stack_alarm
                target: stack
                relationship_type: on
                template_id : alarm_on_stack
            - relationship:
                source: instance
                target: stack
                relationship_type: attached
                template_id : instance_attached_stack
    scenarios:
        - scenario:
            condition: host_contains_instance and alarm_on_stack and not instance_attached_stack
            actions:
                - action:
                   action_type: set_state
                   properties:
                      state: available
                   action_target:
                      target: instance
