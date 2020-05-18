====================================
Vitrage Template Loading - Version 2
====================================

Overview
========

Vitrage templates are defined in yaml with specific format_. During startup,
templates are loaded into ``TemplateData``. After that , scenarios in loaded
templates will be added into scenario repository.

This document explains the implementation details of template data to help
developer understand how scenario_evaluator_ works.

.. _format: vitrage-templates.html
.. _scenario_evaluator: scenario-evaluator.html

Example
=======

Let's take a basic template as example

.. code-block:: yaml

  metadata:
   version: 2
   name: basic_template
   description: basic template for general tests
  definitions:
   entities:
    - entity:
       category: ALARM
       type: nagios
       name: HOST_HIGH_CPU_LOAD
       template_id: alarm
    - entity:
       category: RESOURCE
       type: nova.host
       template_id: resource
   relationships:
    - relationship:
       source: alarm
       target: resource
       relationship_type: on
       template_id : alarm_on_host
  scenarios:
   - scenario:
      condition: alarm_on_host
      actions:
       - action:
          action_type: set_state
          properties:
           state: SUBOPTIMAL
          action_target:
           target: resource

``TemplateData`` will build ``entities``, ``relationships`` and most importantly
``scenarios`` out from the definition.

.. code-block:: python

  expected_entities = {
    'alarm': Vertex(vertex_id='alarm',
                    properties={'vitrage_category': 'ALARM',
                                'vitrage_type': 'nagios',
                                'name': 'HOST_HIGH_CPU_LOAD',
                                }),
    'resource': Vertex(vertex_id='resource',
                       properties={'vitrage_category': 'RESOURCE',
                                   'vitrage_type': 'nova.host',
                                   })
  }

  expected_relationships = {
    'alarm_on_host': EdgeDescription(
      edge=Edge(source_id='alarm',
                target_id='resource',
                label='on',
                properties={'relationship_type': 'on'}),
      source=expected_entities['alarm'],
      target=expected_entities['resource']
    )
  }

  expected_scenario = Scenario(
    id='basic_template-scenario0',
    condition=[
      [ConditionVar(symbol_name='alarm_on_host',
                    positive=True)]],
    actions=[
      ActionSpecs(
        type='set_state',
        targets={'target': 'resource'},
        properties={'state': 'SUBOPTIMAL'})],
    subgraphs=template_data.scenarios[0].subgraphs,  # ignore subgraphs
    entities=expected_entities,
    relationships=expected_relationships
  )

Entities and relationships
==========================

Entities and relationships are loaded into dicts keyed by ``template_id`` so
that the references in scenarios can be resolved quickly.

Note that entities and relationships dicts are **NOT** added to scenario
repository. This implies the scope of ``template_id`` is restricted to one
template file. It is **NOT** global.

It is considered invalid to have duplicated ``template_id`` in one template, but
it is possible that two or more entities have exactly the same properties except
``template_id``. There is an example in
``vitrage/tests/resources/templates/evaluator/high_availability.yaml``:

.. code:: yaml

  - entity:
     category: RESOURCE
     type: nova.instance
     template_id: instance1
  - entity:
     category: RESOURCE
     type: nova.instance
     template_id: instance2

It is used to model scenario contains two or more entities of same type, such
as high availability condition.

Scenarios
=========

``Scenario`` class holds the following properties:

* id
* version
* condition
* actions
* subgraphs
* entities
* relationships
* enabled


id
--

Formatted from template name and scenario index

condition
---------

Condition strings in template are expressions composed of template id and
operators. As explained in embedded comment:

    The condition string will be converted here into DNF (Disjunctive
    Normal Form), e.g., (X and Y) or (X and Z) or (X and V and not W)...
    where X, Y, Z, V, W are either entities or relationships
    more details: https://en.wikipedia.org/wiki/Disjunctive_normal_form

    The condition variable lists is then extracted from the DNF object. It
    is a list of lists. Each inner list represents an AND expression
    compound condition variables. The outer list presents the OR expression

        [[and_var1, and_var2, ...], or_list_2, ...]

    :param condition_str: the string as it written in the template itself
    :return: condition_vars_lists

actions
-------

``actions`` is a list of ``ActionSpecs``.

The action targets in the spec must be referenced in the condition definition.
They are either linked to ``vertex_id`` of entity condition variables or
``source_id`` and ``target_id`` in relationship condition variable extracted.

In each matched subgraph in the entity graph, the targets will be resolved as
concrete vertices or edges.

subgraphs
---------

Sub graphs are built from conditions for pattern matching in the entity graph.
Each sub-list in condition variables list is compiled into one sub graph. The
actions will be triggered if any of the subgraph is matched.

entities & relationships
------------------------

Dicts of **touched** entities and relationships during subgraph building are
saved in scenario.

This makes creation of the scenarios repository index on related entities and
relationships easier and more efficient. You don't need to traverse the
condition object again, which is already done once during subgraphs building.
It also eliminate the necessity of duplication check because there is no
duplicate entities or relationships in these dicts compared to the condition
variables lists.
