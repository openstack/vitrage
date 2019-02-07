========================
Vitrage Evaluator Design
========================

Overview
========

The Vitrage Scenario Evaluator is charged with the evaluation of the
scenarios specified in the Vitrage templates, and executing the actions
associated with these scenarios when they are triggered. The Scenario Evaluator
is also responsible for resolving any inter-action dependencies, such as two
contradicting actions (e.g., raise and disable the same alarm), two overlapping
actions etc.


Evaluator Design
================

::

    +-------------+
    | +-------------+
    | |             |
    | |  Templates  |
    +-+   (YAML)    |
      +-----------+-+
                  |
      +------------------------------------------------------------------------------+
      |Template   |                                                                  |
      |Loading    | load                                                             |
      |           |                                                                  |
      |     +-----v-------------+        +---------------+       +---------------+   |
      |     |   Template Data   |        |               |       |               |   |
      |     |                   |process |   Template    |  add  |   Scenario    |   |
      |     |(Python Dictionary)+-------->    Object     +------->     Repo      |   |
      |     |                   |        |               |       |               |   |
      |     +-------------------+        +---------------+       +---+--------+--+   |
      |                                                              |        ^      |
      |                                                              |        |      |
      |                                                              |        |      |
      +------------------------------------------------------------------------------+
                                                                     |        |
      +-----------------------------------------------------------------------------------+
      | Event Processing                              return relevant|        | get       |
      |                                                  scenarios   |        | scenarios |
      |       +--------------+                 +----------------------------------+       |
      |       |              |    perform      | analyze             |        |   |       |
      |       |  Action      |    action       | matches             |        |   |       |
      |       |  Executor    <--------------------------------+      |        |   |       |
      |       |              |                 |              |      |        |   |       |
      |       |              |                 |              |      |        |   |       |
      |       +--------------+                 +----------------------------------+       |
      |                                                       |      |        |           |
      |                                       return scenario |      |        |           |
      |                                           matches     |      |        |           |
      |                                                 +-----+------v--------+           |
      |                                                 |                     |           |
      |                                                 |    Entity Graph     |           |
      |                                                 |                     |           |
      |                                                 |                     |           |
      |                                                 +---------------------+           |
      +-----------------------------------------------------------------------------------+

Flow
====

Concepts and Guidelines
-----------------------
- *Events:* The Scenario Evaluator is notified of each event in the Entity
  Graph after the event takes place. An event in this context is any change
  (create/update/delete) in a graph element (vertex/edge). The notification
  will consist of two copies of the element: the element *before* the change
  and the *current* element after the change took place.

- *Actions - Do and Undo:* If the Entity Graph matches a scenario, the
  relevant actions will need to be executed. Conversely, if a previously
  matched scenario no longer holds, the action needs to be undone. Thus, for
  each action there must be a "do" and "undo" procedure defined. For example,
  the *raise_alarm* action will raise an alarm in the "do" procedure, and
  disable the alarm in the "undo" procedure. An important feature of this
  approach is that for a given scenario and a specific event, either the "do"
  or "undo" phases can be performed but not both simultaneously.


Template Loading
----------------

Scenarios are written up in configuration files called *templates*. The format
and specification of these can be seen here_.

.. _here: vitrage-templates.html

Templates should all be located in the *<vitrage folder>/templates* folder.

When Vitrage is started up, all the templates are loaded into a *Scenario*
*Repository*. During this loading, template verification is done to
ensure the correct format is used, references are valid, and more. Errors in
each template should be written to the log. Invalid templates are skipped. See
details_.

.. _details: templates-loading.html

The Scenario Repository supports querying for scenarios based on a vertex or
edge in the Entity Graph. Given such a graph element, the Scenario Repository
will return all scenarios where this element appears in the scenario condition.
This means that a corresponding element appears in the scenario condition, such
that for each key-value in the template, the same key-value can be found in the
element (but not always the reverse).

Ongoing Operation
-----------------

1. The Scenario Evaluator is notified of an event on some element in the Entity
   Graph.
2. The Scenario Evaluator queries the Scenario Repository for relevant
   scenarios for both *before* and *current* states of the element, and returns
   a set of matching scenarios for each.
3. The two sets of scenarios are analyzed and filtered, resulting in two
   disjoint sets, to avoid "do/undo" conflicts (See above in
   'Concepts and Guidelines'_).
   Currently, this filtering will be done by removing any scenario that appears
   in both from both sets.
4. For each scenario related to the *before* element, the Scenario Evaluator
   queries the Entity Graph for all the matching patterns in the current
   system. For each match and each associated action, a reference to the
   *undo* of the action is added to an *action collection*.
5. For each scenario related to the *current* element,the Scenario Evaluator
   queries the Entity Graph for all the matching patterns in the current
   system. For each match and each associated action, a reference to the
   *do* of the action is added to the same *action collection*.
6. Given all the actions (do & undo) in the *action collection*, analyze
   the dependencies between themselves, as well as between them and currently
   active actions. The result of this analysis will be a new collection of
   actions comprised of the correct actions to perform. See below in the
   'Dealing with Overlapping Scenarios'_ Section.
7. Given all the actions (do & undo) in the *action collection*, perform them
   using action executor.

   - Currently, the only action filtering is avoiding performing the same
     action twice.


System Initialization
---------------------

During the initialization of Vitrage, the Scenario Evaluator will be
de-activated until all the datasources complete their initial "get_all"
process. After it is activated, the consistency flow will begin, which will
trigger all the relevant scenarios for each element in the Entity Graph.

This approach has several benefits:

- During the initialization period, many events need to be processed into the
  Entity Graph. By postponing the evaluation till after this period, we avoid
  bottlenecks and other performance issues.
- During the initialization period the Entity Graph is built step-by-step until
  it reflects the current status of the Cloud. Thus, during this interim period
  scenarios that contain "not" clauses might be triggered because a certain
  entity is not present in the graph, even though it is present in reality and
  just has not been processed into the graph (since the "get_all" is not
  finished).

It is possible that this late activation of the evaluator will be removed or
changed once we move to a persistent graph database for the Entity Graph in
future version.


Dealing with Overlapping Scenarios
----------------------------------

There can be multiple Vitrage scenarios loaded in a specific system, some of
which might overlap in their targets. For example, two scenarios might have a
"set_state" action, with identical or different states, for the same resource.
We need to deal with such overlaps.
Currently, the goal is to support overlap of the same action type with itself,
specifically the following use cases, which correspond to the three actions
Vitrage supports at this point:

- *set_state:* Two scenarios setting the state of the same resource
- *raise_alarm:* Two scenarios raising the same deduced alarm (with possibly
  different severity)
- *add_causal_relationship:* Two scenarios adding the same causal relationship

For all of these, the desired behavior is to choose the *dominant* outcome or
action. For *set_state* this means the worst state, and for *raise_alarm* this
means the highest severity of all active actions.

In order to support this feature, Vitrage maintains an in-memory record of all
active actions, indexed (broadly) according to their affected target. This
allows for tracking individual actions and their triggers, even when they
overlap in their effect.

For more details on the implementation of this functionality, see the design
on this etherpad_.

.. _etherpad: https://etherpad.openstack.org/p/vitrage-overlapping-templates-support-design
