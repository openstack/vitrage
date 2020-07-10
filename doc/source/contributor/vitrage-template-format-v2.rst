====================================
Vitrage Templates Format - Version 2
====================================

*Note:* Consider using the newer template format version_3_

.. _version_3: https://docs.openstack.org/vitrage/latest/contributor/vitrage-templates.html

Overview
========
In Vitrage we use configuration files, called ``templates``, to express rules
regarding raising deduced alarms, setting deduced states, and detecting/setting
RCA links.
This page describes the format of the Vitrage templates, with some examples and
open questions on extending this format. Additionally, a short guide on adding
templates is presented.

*Note:* This document refers to Vitrage templates version 2. The documentation
of version 1 can be found here_

.. _here: https://docs.openstack.org/vitrage/pike/


Template Structure
==================
The template is written in YAML language, with the following structure:
 ::

  metadata:
    version: <template version>
    name: <unique template identifier>
    type: <one of: standard, definition, equivalence>
    description: <what this template does>
  definitions:
    entities:
        - entity: ...
        - entity: ...
    relationships:
        - relationship: ...
        - relationship: ...
  includes:
        - name: <name as stated in the metadata of a definition template>
        - name: ...
  scenarios:
      - scenario:
          condition: <if statement true do the action>
          actions:
              - action: ...


The template is divided into four main sections:

- *metadata:* Contains general information about the template.

  - *version -* the version of the template format. The default is 1.
  - *name -* the name of the template
  - *type -* the type of the template. Should be one of: standard, definition, equivalence
  - *description -* a brief description of what the template does (optional)
- *definitions:* This section is **mandatory** unless an include section is specified in the template (see below).
  This section contains the atomic definitions referenced later on, for entities and relationships.

  - *entities –* describes the resources and alarms which are relevant to the template scenario (conceptually, corresponds to a vertex in the entity graph)
  - *relationships –* the relationships between the entities (conceptually, corresponds to an edge in the entity graph)
- *includes:* This section is optional. If included, it must contain a list of names of definition templates as they appear in the metadata section of said templates.
  If only definitions from included definition templates are used to create scenarios within the template, then the *definitions* section is **optional**.
- *scenarios:* A list of if-then scenarios to consider. Each scenario is comprised of:
  - *condition –* the condition to be met. This condition will be phrased referencing the entities and relationships previously defined.
  - *action(s) –* a list of actions to execute when the condition is met.


Definition Template Structure
-----------------------------
These are separate files, which contain only definitions and can be included under the includes section in regular templates. The definition templates are written in YAML
language, with the following structure:

 ::

  metadata:
    version: 2
    name: <unique definition template identifier. Used in the includes section of regular templates>
    type: definition
    description: <what definitions this template contains>
  definitions:
    entities:
        - entity: ...
        - entity: ...
    relationships:
        - relationship: ...
        - relationship: ...

A definition template is in same format as a regular template -
except it **does not** contain a scenarios or an includes section. Once included in a
template, the definition template's entities and relationships can be used within the template
they are included to create scenarios.

Condition Format
----------------
The condition which needs to be met will be phrased using the entities and
relationships previously defined. An expression is either a *single* entity,
or some logical combination of relationships.
Expression can be combined using the following logical operators:

- "and" - indicates both expressions must be satisfied in order for the
  condition to be met.
- "or" - indicates at least one expression must be satisfied in order for the
  condition to be met (non-exclusive or).
- "not" - indicates that the expression must not be satisfied in order for the
  condition to be met.
- parentheses "()"  - clause indicating the scope of an expression.

The following are examples of valid expressions, where X, Y and Z are
relationships:

- X
- X and Y
- X and Y and Z
- X and not Y
- X and not (Y or Z)
- X and not X


A few restrictions regarding the condition format:

* A condition can not be entirely "negative", i.e. it must have at least one
  part that does not have a "not" in front of it.

  For example, instead of:
   not alarm_on_instance
  use:
   instance and not alarm_on_instance

* There must be at least one entity that is common to all "or" clauses.

  For example, this condition is illegal:
   alarm1_on_host or alarm2_on_instance
  This condition is legal:
   alarm1_on_instance or alarm2_on_instance


For more information, see the 'Calculate the action_target' section in
`External Actions Spec <https://specs.openstack.org/openstack/vitrage-specs/specs/pike/external-actions.html>`_


Template validation status codes
--------------------------------

.. toctree::
   :maxdepth: 1

   template_validation_status_code

Examples
========

Example 1: Basic RCA and Deduced Alarm/State
--------------------------------------------
The following template demonstrates

1. How to raise a deduced alarm. Specifically, if there is high CPU load on a
   host, raise alarm indicating CPU performance problems on all contained
   instances.
2. How to link alarms for purposes of root cause analysis (RCA). Specifically,
   if there is high CPU load on the host and CPU performance problems on the
   hosted instances, we link them with a "causes" relationship.
3. How to use a single template for several different scenarios.

 ::

    metadata:
        version: 2
        name: host_high_mem_load_to_instance_mem_suboptimal
        type: standard
        description: when there is high memory on the host, show implications on the instances
    definitions:
        entities:
            - entity:
                category: ALARM
                name: host_high_mem_load
                template_id: host_alarm # some string
            - entity:
                category: ALARM
                name: instance_mem_performance_problem
                template_id: instance_alarm
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
            condition: alarm_on_host and host_contains_instance # condition uses relationship ids
            actions:
                - action:
                   action_type: raise_alarm
                   properties:
                      alarm_name: instance_mem_performance_problem
                      severity: warning
                   action_target:
                      target: instance # entity template_id
                - action:
                   action_type: set_state
                   properties:
                      state: suboptimal
                   action_target:
                      target: instance # entity template_id
        - scenario:
            condition: alarm_on_host and alarm_on_instance and host_contains_instance
            actions:
                - action:
                   action_type: add_causal_relationship
                   action_target:
                      source: host_alarm
                      target: instance_alarm

Example 2: Deduced state based on alarm
---------------------------------------
The following template will change the state of a resource to "ERROR" if there
is any alarm of severity "CRITICAL" on it.

 ::

    metadata:
        id: deduced_state_for_all_with_alarm
        description: deduced state for all resources with alarms
    definitions:
        entities:
            - entity:
                category: RESOURCE
                template_id: a_resource # entity ids are any string
            - entity:
                category: ALARM
                severity: critical
                template_id: high_alarm # entity ids are any string
        relationships:
            - relationship:
                source: high_alarm
                target: a_resource
                relationship_type: on
                template_id : high_alarm_on_resource
    scenarios:
        - scenario:
            condition: high_alarm_on_resource
            actions:
                - action:
                   action_type : set_state
                   properties:
                      state: error
                   action_target:
                      target: a_resource

Example 3: Deduced alarm based on state
---------------------------------------
This template will cause an alarm to be raised on any Host in state "ERROR"

Note that in this template, there are no relationships. The condition is just
that the entity exists. Also note that the states and severity are
case-insensitive.

 ::

    metadata:
        version: 2
        name: deduced_alarm_for_all_host_in_error
        type: standard
        description: raise deduced alarm for all hosts in error
    definitions:
        entities:
            - entity:
                category: RESOURCE
                type: nova.host
                state: error
                template_id: host_in_error
    scenarios:
        - scenario:
            condition: host_in_error
            actions:
                - action:
                   action_type: raise_alarm
                   properties:
                      alarm_name: host_in_error_state
                      severity: critical
                   action_target:
                      target: host_in_error

Example 4: Deduced Alarm triggered by several options
-----------------------------------------------------
This template will raise a deduced alarm on an instance, which can be caused by
an alarm on the hosting zone or an alarm on the hosting host.

 ::

    metadata:
        version: 2
        name: deduced_alarm_two_possible_triggers
        type: standard
        description: deduced alarm using or in condition
    definitions:
        entities:
            - entity:
                category: ALARM
                name: zone_connectivity_problem
                template_id: zone_alarm
            - entity:
                category: ALARM
                name: host_connectivity_problem
                template_id: host_alarm
            - entity:
                category: RESOURCE
                type: nova.zone
                template_id: zone
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
                source: zone_alarm
                target: zone
                relationship_type: on
                template_id : alarm_on_zone
            - relationship:
                source: zone_alarm
                target: zone
                relationship_type: on
                template_id : alarm_on_host
            - relationship:
                source: zone
                target: host
                relationship_type: contains
                template_id : zone_contains_host
            - relationship:
                source: host
                target: instance
                relationship_type: contains
                template_id : host_contains_instance
    scenarios:
        - scenario:
            condition: (alarm_on_host and host_contains_instance) or (alarm_on_zone and zone_contains_host and host_contains_instance)
            actions:
                - action:
                   action_type : raise_alarm
                   properties:
                      alarm_name: instance_connectivity_problem
                      severity: critical
                   action_target:
                      target: instance


Usage
=====

Adding/removing a template
--------------------------

- Ensure all the templates you wish to use are placed here: *<vitrage folder>/templates*.
- Restart *vitrage-graph*.
- The template will be validated before loading. Validation errors are written
  to the log. Templates with validation errors are skipped.

Common properties and their acceptable values - for writing templates
---------------------------------------------------------------------

+-------------------+-----------------------+-------------------------+------------------------------------+
| block             | key                   | supported values        | comments                           |
+===================+=======================+=========================+====================================+
| entity            | category              | ALARM                   |                                    |
|                   |                       | RESOURCE                |                                    |
+-------------------+-----------------------+-------------------------+------------------------------------+
| entity (ALARM)    | type                  | any string              |                                    |
+-------------------+-----------------------+-------------------------+------------------------------------+
| entity (RESOURCE) | type                  | openstack.cluster,      | These are for the datasources that |
|                   |                       | nova.zone,              | come with vitrage by default.      |
|                   |                       | nova.host,              | Adding datasources will add more   |
|                   |                       | nova.instance,          | supported types, as defined in the |
|                   |                       | cinder.volume,          | datasource transformer             |
|                   |                       | switch                  |                                    |
+-------------------+-----------------------+-------------------------+------------------------------------+
| action            | action_type           | raise_alarm,            |                                    |
|                   |                       | set_state,              |                                    |
|                   |                       | add_causal_relationship,|                                    |
|                   |                       | mark_down,              |                                    |
|                   |                       | execute_mistral         |                                    |
+-------------------+-----------------------+-------------------------+------------------------------------+

Using regular expressions in an entity definition
-------------------------------------------------
All properties within an entity definition can be made to include regular
expressions. To do this, simply add ".regex" to their key. For example, as
Zabbix supports regular expressions and a Zabbix alarm contains a "rawtext"
field which is a regular expression, a Zabbix alarm entity defined in the
template may contain a "rawtext.regex" field that is also defined by a
regular expression:
::

  - entity:
     category: ALARM
     type: zabbix
     rawtext.regex: Interface ([_a-zA-Z0-9'-]+) down on {HOST.NAME}
     template_id: zabbix_alarm

Using parameters
----------------
On version 2, some properties in the template definition can be defined as
parameters and assigned with actual values upon template creation. This allows
easy reuse of a similar template structure for different alarm types.

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


Actual values for the parameters must be given upon template creation, for
example:

::

  vitrage template add --path template_with_params.yaml --params template_name='High CPU load on host' alarm_type='High CPU load'


In the example below, `vitrage template add` should be called with parameters:

* template_name
* host_alarm_name
* instance_alarm_name
* instance_alarm_severity (optional)

::

    metadata:
        version: 2
        name: get_name(template_name)
        type: standard
        description: host alarm affects its instances
    parameters:
        template_name:
        host_alarm_name:
            description: the name of the zabbix alarm that is reported on the host
        instance_alarm_name:
            description: the name of the vitrage deduced alarm to raise on the instance
        instance_alarm_severity:
            description: the severity of the vitrage deduced alarm to raise on the instance
            default: WARNING
    definitions:
        entities:
            - entity:
                category: ALARM
                type: zabbix
                rawtext: get_param(host_alarm_name)
                template_id: host_alarm
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
                source: host_alarm
                target: host
                relationship_type: on
                template_id : alarm_on_host
            - relationship:
                source: host
                target: instance
                relationship_type: contains
                template_id : host_contains_instance
    scenarios:
        - scenario:
            condition: alarm_on_host and host_contains_instance
            actions:
                - action:
                   action_type : raise_alarm
                   properties:
                      alarm_name: get_param(instance_alarm_name)
                      severity: get_param(instance_alarm_severity)
                   action_target:
                      target: instance



Using functions in an action definition
---------------------------------------
Some properties of an action can be defined using functions. On version 2, one
function is supported: get_attr, and it is supported only for execute_mistral
action.

*Note:* Functions are supported from version 2 and on.

get_attr
^^^^^^^^
This function retrieves the value of an attribute of an entity that is defined
in the template.

Usage
~~~~~

get_attr(template_id, attr_name)

Example
~~~~~~~
::

   scenario:
     condition: alarm_on_host_1
     actions:
       action:
         action_type: execute_mistral
         properties:
           workflow: demo_workflow
           input:
             host_name: get_attr(host_1,name)
             retries: 5


get_param
^^^^^^^^^
See `Using parameters`_


Supported Actions
-----------------

raise_alarm
^^^^^^^^^^^
Raise a deduced alarm on a target entity
 ::

    action:
        action_type : raise_alarm
            properties:
                alarm_name: some problem # mandatory; string that is valid variable name
                severity: critical       # mandatory; should match values in "vitrage.yaml"
            action_target:
                target: instance         # mandatory. entity (from the definitions section) to raise an alarm on. Should not be an alarm.

set_state
^^^^^^^^^
Set state of specified entity. This will directly affect the state as seen in vitrage, but will not impact the state at the relevant datasource of this entity.
 ::

    action:
        action_type : set_state
            properties:
                state: error # mandatory; should match values in the relevant datasource_values YAML file for this entity.
            action_target:
                target: host # mandatory. entity (from the definitions section) to change state


add_causal_relationship
^^^^^^^^^^^^^^^^^^^^^^^
Add a causal relationship between alarms.
 ::

    action:
        action_type : add_causal_relationship
            action_target:
                source: host_alarm     # mandatory. the alarm that caused the target alarm (name from the definitions section)
                target: instance_alarm # mandatory. the alarm that was caused by the source alarm (name from the definitions section)


mark_down
^^^^^^^^^
Set an entity marked_down field.
This can be used along with nova notifier to call force_down for a host
::

   action:
        action_type : mark_down
            action_target:
                target: host # mandatory. entity (from the definitions section, only host) to be marked as down


execute_mistral
^^^^^^^^^^^^^^^
Execute a Mistral workflow.
If the Mistral notifier is used, the specified workflow will be executed with
its parameters.
::

   action:
        action_type: execute_mistral
        properties:
            workflow: demo_workflow                # mandatory. The name of the workflow to be executed
            input:                                 # optional. A list of properties to be passed to the workflow
               farewell: Goodbye and Good Luck!
               employee: John Smith


Future support & Open Issues
============================

Inequality
----------
Consider a template that has two entities of the same category+type, say E1 and
E2 both are instances like this:

 ::

    metadata:
        version: 2
        name: two_similar_instances
        type: standard
    definitions:
        entities:
            - entity:
                category: RESOURCE
                type: nova.host
                template_id: host
            - entity:
                category: RESOURCE
                type: nova.instance
                template_id: instance1
            - entity:
                category: RESOURCE
                type: nova.instance
                template_id: instance2
            ...
        relationships:
            - relationship:
                source: host
                target: instance1
                relationship_type: contains
                template_id: link1
            - relationship:
                source: host
                target: instance2
                relationship_type: contains
                template_id: link2

            ...

There are three options of how to interpret this template:

- *instance1 == instance2.* This option is not a reasonable one, as in this
  case the template can be written with only *instance1*
- *instance1 != instance2.*
- *instance1 != instance2 or instance1 == instance2.* In other words, either
  option is fine.

Thus, we need a way to distinguish between options 2 & 3 (as option 1 can be
expressed by using only instance1). This can be done in two ways:
1. Introducing another logical operator "neq", to be used between expressions:

 ::

    condition: (instance1 neq instance2) and...

2. Using this as a relationship type "neq":

 ::

    relationship:
        source: instance1
        target: instance2
        relationship_type: neq


Cardinality
-----------
To support cardinality, for example to express we want a host to have two
instances on it, we could take different approaches.

1. One approach would rely on the "neq" relationship described above. Similar
to the example given in the previous section, stating that the two instances on
the host are not equal is equivalent to a cardinality of two.
2. A different approach would be to expand the definition of the "relationship"
clause. By default cardinality=1 (which will support backward compatibility)

For example, we might use the one of the following formats

::

    - relationship: # option A
        source: host
        target: instance
        target_cardinality: 2 # two instances, but only one host
        relationship_type: contains
        template_id: host_contains_two_instances_A

    - relationship: # option B, same as option A but split into two lines
        source: host
        target: instance
        cardinality_for: target
        cardinality: 2
        relationship_type: contains
        template_id: host_contains_two_instances_B
