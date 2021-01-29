====================
Vitrage manual tests
====================

General
-------

The purpose of these tests is to manually check functionality that is not
tested using tempest tests, and to double-check the correctness and validity of
a devstack in general.

Vitrage Health
--------------

Services
^^^^^^^^

Services Status
~~~~~~~~~~~~~~~
**Run**

.. code:: bash

  sudo systemctl status devstack@vitrage-graph.service
  sudo systemctl status devstack@vitrage-persistor.service
  sudo systemctl status devstack@vitrage-notifier.service
  sudo systemctl status devstack@vitrage-api.service

**Expected result**

Make sure that the status is ``active``.

Check the logs for WARNING/ERROR/Exception/traceback

Services Restart
~~~~~~~~~~~~~~~~
**Run**

.. code:: bash

  sudo service devstack@vitrage-graph restart
  sudo service devstack@vitrage-notifier restart
  sudo service devstack@vitrage-persistor restart

**Expected result**

Make sure the restart is quick and does not reach a timeout

Services Information
~~~~~~~~~~~~~~~~~~~~
**Run**

.. code:: bash

  vitrage service list

**Expected result**

.. code:: bash

  +----------------------------------+------------+-------------+---------------------------+
  | Name                             | Process Id | Hostname    | Created At                |
  +----------------------------------+------------+-------------+---------------------------+
  | ApiWorker worker(0)              |       1084 | my-devstack | 2019-03-13T14:31:46+00:00 |
  | EvaluatorWorker worker(0)        |       1082 | my-devstack | 2019-03-13T14:31:46+00:00 |
  | MachineLearningService worker(0) |       5956 | my-devstack | 2019-03-13T10:30:54+00:00 |
  | PersistorService worker(0)       |      22536 | my-devstack | 2019-03-13T14:14:15+00:00 |
  | SnmpParsingService worker(0)     |       6170 | my-devstack | 2019-03-13T10:30:56+00:00 |
  | VitrageNotifierService worker(0) |      22746 | my-devstack | 2019-03-13T14:14:27+00:00 |
  | vitrageuWSGI worker 1            |       2847 | my-devstack | 2019-03-13T10:30:47+00:00 |
  | vitrageuWSGI worker 2            |       2848 | my-devstack | 2019-03-13T10:30:47+00:00 |
  +----------------------------------+------------+-------------+---------------------------+

Processes
~~~~~~~~~

**Run**

.. code:: bash

  ps -aux | grep vitrage-graph


**Expected result**

vitrage-graph: master process

vitrage-graph: EvaluatorWorker

vitrage-graph: ApiWorker

There may be more than one EvaluatorWorker processes, according to the
definition in vitrage.conf (the default is one worker).


Healthcheck API
^^^^^^^^^^^^^^^

**Run**

.. code:: bash

  vitrage healthcheck


**Expected result**

.. code:: bash

  +----------+---------+
  | Field    | Value   |
  +----------+---------+
  | detailed | False   |
  | reasons  | ['OK'] |
  +----------+---------+

Vitrage Help
^^^^^^^^^^^^

**Run**

.. code:: bash

  vitrage -h

**Expected result**

Should display all Vitrage commands.

CLI commands
------------
Most of the functionality is covered in tempest tests, but we have no automatic
tests for the CLI itself.

Topology
^^^^^^^^

**Run**

.. code:: bash

  vitrage topology show

**Expected result**

Should display a graph with Vitrage entities and relationships.

Templates
^^^^^^^^^
Template Validate
~~~~~~~~~~~~~~~~~

+----------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                                | Expected results                                       |
+================================================================+========================================================+
| vitrage template validate                                      | Error, --path is required                              |
+----------------------------------------------------------------+--------------------------------------------------------+
| vitrage template validate -path ./v1_template.yaml             | Validation failed - Unknown template type              |
+----------------------------------------------------------------+--------------------------------------------------------+
| vitrage template validate --path ./v1_template.yaml            | Template validation is OK                              |
| --type standard                                                |                                                        |
+----------------------------------------------------------------+--------------------------------------------------------+
| vitrage template validate --path ./v1_template.yaml            | Validation failed, definition template can not contain |
| --type definition                                              | ``scenarios`` block                                    |
+----------------------------------------------------------------+--------------------------------------------------------+
| vitrage template validate --path ./v2_high_cpu_load.yaml       | Template validation is OK                              |
+----------------------------------------------------------------+--------------------------------------------------------+
| vitrage template validate --path .                             | Validates all templates in the path. Some succeed and  |
|                                                                | some fail.                                             |
+----------------------------------------------------------------+--------------------------------------------------------+
| vitrage template validate --path ./v2_definition_template.yaml | Template validation is OK                              |
+----------------------------------------------------------------+--------------------------------------------------------+
| vitrage template validate --path v2_equivalence.yaml           | No validation                                          |
+----------------------------------------------------------------+--------------------------------------------------------+
| vitrage template validate --path v3_high_mem_consumption.yaml  | Template validation is OK                              |
+----------------------------------------------------------------+--------------------------------------------------------+

Template Add
~~~~~~~~~~~~

+----------------------------------------------------------------+---------------------------------------------------------+
| What to execute                                                | Expected results                                        |
+================================================================+=========================================================+
| vitrage template list                                          | An empty list                                           |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add                                           | Error, --path is required                               |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path ./v1_template.yaml                 | Template added with status ERROR: Unknown template type |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path ./v1_template.yaml                 | --type: invalid choice: ``kuku``                        |
| --type kuku                                                    |                                                         |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path ./v1_template.yaml                 | Template added with status LOADING                      |
| --type standard                                                |                                                         |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path ./v1_template.yaml                 | ERROR: Duplicate template name                          |
| --type standard                                                |                                                         |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template list                                          | One template with status ACTIVE                         |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template delete                                        | No output                                               |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template list                                          | An empty list                                           |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path ./v2_high_cpu_load.yaml            | Template added with status LOADING                      |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path ./v2_definition_template.yaml      | Template added with status LOADING                      |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path ./v2_with_include.yaml             | Template added with status LOADING                      |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path ./v2_with_invalid_include.yaml     | ERROR: Trying to include a template that does not exist |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path v2_equivalence.yaml                | Template added with status LOADING                      |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path v3_high_mem_consumption.yaml       | Template validation is OK                               |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template list                                          | Five templates with status ACTIVE and one in ERROR      |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template show <uuid>                                   | Shows the template json representation                  |
+----------------------------------------------------------------+---------------------------------------------------------+

Templates with parameters
~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------------------------------------------------------+---------------------------------------------------------+
| What to execute                                                | Expected results                                        |
+================================================================+=========================================================+
| vitrage template validate --path v3_with_params.yaml           | Failed to resolve parameter - template_name             |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template validate --path v3_with_params.yaml           | Template validation is OK                               |
| --params template_name=template1                               |                                                         |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template validate --path v3_with_params.yaml           | Failed to resolve parameter - template_name             |
| --params alarm_name=alarm1                                     |                                                         |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template validate --path v3_with_params.yaml           | Template validation is OK                               |
| --params template_name=template1 alarm_name=alarm1             |                                                         |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path v3_with_params.yaml                | Template added with status LOADING                      |
| --params template_name=template1 alarm_name=alarm1             |                                                         |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template add --path v2_with_params.yaml                | Template added with status LOADING                      |
| --params template_name=t1 alarm_name=a1 alarm_type=zabbix      |                                                         |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage template show <uuid>                                   | Shows the template json representation. All parameters  |
|                                                                | are resolved and the ``parameters`` section is removed. |
+----------------------------------------------------------------+---------------------------------------------------------+

Deduced Alarms and RCA
^^^^^^^^^^^^^^^^^^^^^^

+----------------------------------------------------------------+---------------------------------------------------------+
| What to execute                                                | Expected results                                        |
+================================================================+=========================================================+
| create an instance in Nova                                     | An instance is created                                  |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage alarm list                                             | An empty list                                           |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage event post --type="High CPU load" --details='          | Make sure to use ``hostname`` that contains an instance |
| {"hostname": "my-devstack","source":"sample_monitor",          | No output                                               |
| "cause":"link-down","severity":"critical","status":"down",     |                                                         |
| "monitor_id":"monitor-1","monitor_event_id":"123"}'            |                                                         |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage alarm list                                             | Shows 'High CPU load' on the host and also an alarm on  |
|                                                                | the instance.                                           |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage alarm show <uuid>                                      | Shows the alarm details. Verify for both alarms.        |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage rca show <uuid>                                        | Shows the alarm RCA graph. Verify for both alarms.      |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage alarm count                                            | Shows one WARNING and one CRITICAL alarm                |
+----------------------------------------------------------------+---------------------------------------------------------+

Resources
^^^^^^^^^

+----------------------------------------------------------------+---------------------------------------------------------+
| What to execute                                                | Expected results                                        |
+================================================================+=========================================================+
| vitrage resource list                                          | Shows a list of resources from different datasources.   |
|                                                                | Does not show alarms                                    |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage resource list --filter ..... TBD                       | Shows a list of resources that match the given filter.  |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage resource show <uuid>                                   | Shows a the defails of the selected resource.           |
+----------------------------------------------------------------+---------------------------------------------------------+
| vitrage resource count                                         | Shows how many resources there are of every type.       |
+----------------------------------------------------------------+---------------------------------------------------------+

Multi Tenancy
^^^^^^^^^^^^^

TBD

Datasources
-----------

**Note:** The resources and alarms are visible only to the tenant that created
them.

* For a resource that was created in the UI, check the Vitrage entity graph of
  the same tenant.
* For a resource that was created in the CLI, check the Vitrage entity graph
  of ``admin`` tenant.

Basic OpenStack datasources
^^^^^^^^^^^^^^^^^^^^^^^^^^^

+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| Create an instance/volume/network/stack                    | A new entity immediately appears in Vitrage entity     |
|                                                            | graph and is connected to the right neighbors.         |
+------------------------------------------------------------+--------------------------------------------------------+
| Delete these resources                                     | The entities are immediately removed from the graph    |
+------------------------------------------------------------+--------------------------------------------------------+

Static Topology
^^^^^^^^^^^^^^^

+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| Copy switch_and_nic.yaml under                             | The switche and nic should appear in the graph within  |
| /etc/vitrage/static_datasources                            | 30 seconds                                             |
+------------------------------------------------------------+--------------------------------------------------------+

Aodh
^^^^

+-------------------------------------------------------------+---------------------------------------------------------+
| What to execute                                             | Expected results                                        |
+=============================================================+=========================================================+
| aodh alarm create --name 'test_1' --state alarm             | An alarm is created in Aodh with state ``alarm``.       |
| --event-type 'my.event' --type event --query                | Make sure to use as traits.resource_id the name of      |
| 'traits.resource_id=string::my-devstack'                    | your devstack.                                          |
+-------------------------------------------------------------+---------------------------------------------------------+
| vitrage alarm list                                          | The Aodh alarm appears and is connected to the devstack |
+-------------------------------------------------------------+---------------------------------------------------------+
| aodh alarm create --name 'Gnocchi alarm 1' --type           | An alarm is created in Aodh with state ``alarm``.       |
| gnocchi_resources_threshold --resource-type instance        | Make sure to assign --resource-id with a valid instance |
| --resource-id f9335fc1-f3bf-4915-bed2-2c7350628ac9 --metric | uuid.                                                   |
| cpu_util --threshold 0.001 --granularity 300  --state alarm |                                                         |
| --aggregation-method mean --comparison-operator gt          |                                                         |
+-------------------------------------------------------------+---------------------------------------------------------+
| vitrage alarm list                                          | Two Aodh alarms, connected to different resources       |
+-------------------------------------------------------------+---------------------------------------------------------+
| aodh alarm delete <alarm UUID>                              |                                                         |
+-------------------------------------------------------------+---------------------------------------------------------+
| vitrage alarm list                                          | One Aodh alarm remains                                  |
+-------------------------------------------------------------+---------------------------------------------------------+

Notifiers
---------

Nova Notifier
^^^^^^^^^^^^^

+-------------------------------------------------------------+---------------------------------------------------------+
| What to execute                                             | Expected results                                        |
+=============================================================+=========================================================+
| vitrage template add --path ./host_down.yaml                | Template added with status LOADING                      |
+-------------------------------------------------------------+---------------------------------------------------------+
| nova service-list                                           | The state of nova-compute is ``up``                     |
+-------------------------------------------------------------+---------------------------------------------------------+
| vitrage event post --type="compute.host.down" --details=    | Make sure to use ``hostname`` of your devstack.         |
| '{"hostname": "my-devstack","source":"sample_monitor",      | No output.                                              |
| "cause":"link-down","severity":"critical","status":"down",  |                                                         |
| "monitor_id":"monitor-1","monitor_event_id":"123"}'         |                                                         |
+-------------------------------------------------------------+---------------------------------------------------------+
| vitrage alarm list                                          | A compute.host.down alarm, connected to the right host  |
+-------------------------------------------------------------+---------------------------------------------------------+
| nova service-list                                           | The state of nova-compute is ``down``                   |
+-------------------------------------------------------------+---------------------------------------------------------+
| vitrage event post --type="compute.host.down" --details=    | Make sure to use ``hostname`` of your devstack.         |
| '{"hostname": "my-devstack","source":"sample_monitor",      | No output.                                              |
| "cause":"link-down","severity":"critical","status":"up",    |                                                         |
| "monitor_id":"monitor-1","monitor_event_id":"123"}'         |                                                         |
+-------------------------------------------------------------+---------------------------------------------------------+
| nova service-list                                           | The state of nova-compute is ``up``                     |
+-------------------------------------------------------------+---------------------------------------------------------+

Webhook Notifier
^^^^^^^^^^^^^^^^

Configure a web client
~~~~~~~~~~~~~~~~~~~~~~
Copy test_web_server.py under /opt/stack
Run: sudo pip install web.py

Test the Webhook Notifier
~~~~~~~~~~~~~~~~~~~~~~~~~

+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| vitrage webhook list                                       | Empty list                                             |
+------------------------------------------------------------+--------------------------------------------------------+
| python /opt/stack/test_web_server.py 8001                  | server started (in a different console window)         |
+------------------------------------------------------------+--------------------------------------------------------+
| python /opt/stack/test_web_server.py 8002                  | server started (in a different console window)         |
+------------------------------------------------------------+--------------------------------------------------------+
| vitrage webhook add --url http://localhost:8001/alarm      | Outputs the webhook details                            |
+------------------------------------------------------------+--------------------------------------------------------+
| vitrage webhook add --url http://localhost:8002/alarm      | Outputs the webhook details                            |
| --regex '{"vitrage_type": "doctor"}'                       |                                                        |
+------------------------------------------------------------+--------------------------------------------------------+
| vitrage webhook list                                       | A list with the details of both webhooks               |
+------------------------------------------------------------+--------------------------------------------------------+
| vitrage webhook show <webhook uuid>                        | Shows the details of the webhook                       |
+------------------------------------------------------------+--------------------------------------------------------+
| vitrage event post --type="compute.host.down" --details=   | Both webhooks print the details of compute.host.down   |
| '{"hostname": "compute-0-0","source":"sample_monitor",     | alarm to the console. The webhook on port 8001 prints  |
| "cause":"link-down","severity":"critical","status":"down", | also the details of the deduced alarms to the console. |
| "monitor_id":"monitor-1","monitor_event_id":"123"}'        |                                                        |
+------------------------------------------------------------+--------------------------------------------------------+
| vitrage webhook delete <webhook uuid>                      | Deletes a webhook                                      |
+------------------------------------------------------------+--------------------------------------------------------+
| vitrage webhook list                                       | Shows only one webhook                                 |
+------------------------------------------------------------+--------------------------------------------------------+
| vitrage event post --type="compute.host.down" --details=   | The deleted webhook does not print anything. The other |
| '{"hostname": "compute-0-0","source":"sample_monitor",     | webhook prints the cleared alarm(s).                   |
| "cause":"link-down","severity":"critical","status":"up",   |                                                        |
| "monitor_id":"monitor-1","monitor_event_id":"123"}'        |                                                        |
+------------------------------------------------------------+--------------------------------------------------------+

Mistral Notifier
^^^^^^^^^^^^^^^^

+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| mistral workflow-create ./workflow1.yaml                   | The workflow is created                                |
+------------------------------------------------------------+--------------------------------------------------------+
| vitrage template add --path ./v3_execute_mistral.yaml      | Template added with status LOADING                     |
+------------------------------------------------------------+--------------------------------------------------------+
| vitrage event post --type="alarm_for_mistral" --details=   | Make sure to use ``hostname`` of your devstack.        |
| '{"hostname": "my-devstack","source":"sample_monitor",     | No output.                                             |
| "cause":"link-down","severity":"critical","status":"down", |                                                        |
| "monitor_id":"monitor-1","monitor_event_id":"123"}'        |                                                        |
+------------------------------------------------------------+--------------------------------------------------------+
| mistral execution-list                                     | ``workflow1`` is in the list.                          |
+------------------------------------------------------------+--------------------------------------------------------+
| mistral execution-get <uuid of the latest execution>       | Shows details about ``workflow1`` execution.           |
+------------------------------------------------------------+--------------------------------------------------------+
| mistral execution-get-input <uuid of the latest execution> | "farewell": "my-devstack"                              |
+------------------------------------------------------------+--------------------------------------------------------+

Zaqar Notifier
^^^^^^^^^^^^^^
TBD

SNMP Notifier
^^^^^^^^^^^^^
TBD

UI Tests
--------

The UI tests are included in this document, so we'll have a complete set of
manual sanity tests in one place.

Alarm Banner
^^^^^^^^^^^^
+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| Go to compute->instances menu                              | The alarm banner should be on the top right corner     |
|                                                            | with the correct number of alarms                      |
+------------------------------------------------------------+--------------------------------------------------------+
| Click on the alarm banner                                  | You should be redirected to Vitrage alarms view        |
+------------------------------------------------------------+--------------------------------------------------------+

Alarm View
^^^^^^^^^^
+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| Raise an alarm of type ``doctor`` (examples above)         | The alarm appears in the ``Active Alarms`` list        |
+------------------------------------------------------------+--------------------------------------------------------+
| Filter By alarm type ``doctor``                            | Only ``doctor`` alarms remain                          |
+------------------------------------------------------------+--------------------------------------------------------+
| Clear the ``doctor`` filter                                | All alarms appear                                      |
+------------------------------------------------------------+--------------------------------------------------------+
| Sort by name                                               | Alarms are sorted                                      |
+------------------------------------------------------------+--------------------------------------------------------+
| Click the RCA button for the ``High CPU load`` alarm       | An RCA graph displays the alarms on the host and on    |
|                                                            | the instance(s). Make sure all properties are ok.      |
+------------------------------------------------------------+--------------------------------------------------------+
| Switch to ``Alarm History`` tab                            | Several alarms should appear with different statuses.  |
|                                                            | The alarms that are currently active should not have   |
|                                                            | an ``Ended`` value.                                    |
+------------------------------------------------------------+--------------------------------------------------------+
| Click the RCA button for one of the alarms                 | An RCA graph displays the alarm(s) as inactive.        |
+------------------------------------------------------------+--------------------------------------------------------+
| Change the ``Ended`` filter and click ``Fetch Alarms``     | The list of alarms is different                        |
+------------------------------------------------------------+--------------------------------------------------------+
| Filter By resource type ``nova.host``                      | Only alarms on the host are displayed                  |
+------------------------------------------------------------+--------------------------------------------------------+
| Go back to ``Active Alarms``                               | The list of active alarms is displayed                 |
+------------------------------------------------------------+--------------------------------------------------------+

Topology View
^^^^^^^^^^^^^
+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| Go to ``Topology View``                                    | The sunburst shows the compute hierarchy in different  |
|                                                            | colors.                                                |
+------------------------------------------------------------+--------------------------------------------------------+
| Switch tenants                                             | The number of instances changes accordingly            |
+------------------------------------------------------------+--------------------------------------------------------+
| Drill down to the host and instances                       | The sunburst changes. On the left there may be alarms  |
+------------------------------------------------------------+--------------------------------------------------------+
| Click the RCA button on one of the alarms                  | The RCA view is opened                                 |
+------------------------------------------------------------+--------------------------------------------------------+

Entity Graph
^^^^^^^^^^^^
+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| Open the ``Entity Graph``, zoom in and out                 | The graph changes accordingly                          |
+------------------------------------------------------------+--------------------------------------------------------+
| Click the ``Pin`` button, drag 1-2 entities, and refresh   | The graph is not changed                               |
+------------------------------------------------------------+--------------------------------------------------------+
| Click the ``Unpin`` button                                 | The graph is changed                                   |
+------------------------------------------------------------+--------------------------------------------------------+
| Double-click two entites to pin them and drag them to      | The pinned entities stay in the same location.         |
| different places. Then refresh the graph.                  | The rest of the graph is changed.                      |
+------------------------------------------------------------+--------------------------------------------------------+
| Click several entities, one at the time                    | The properties of the selected entity appear on the    |
|                                                            | left panel                                             |
+------------------------------------------------------------+--------------------------------------------------------+
| Write a text in the search box                             | All entities with the selected text are highlighted    |
+------------------------------------------------------------+--------------------------------------------------------+
| Switch to a different tenant and see how the graph changes | There are less entities (all instances are gone)       |
+------------------------------------------------------------+--------------------------------------------------------+
| Filter by a specific Heat stack, modify the details level  | The graph changes accordingly                          |
+------------------------------------------------------------+--------------------------------------------------------+

Template View
^^^^^^^^^^^^^
Template View for tenant
~~~~~~~~~~~~~~~~~~~~~~~~
+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| Open the ``Template`` view under ``Project->Vitrage``,     | Few templates appear with ``Template validation is OK``|
| check the list of templates                                | Details.                                               |
|                                                            | There are no Add and Delete buttons.                   |
+------------------------------------------------------------+--------------------------------------------------------+
| Write a name in the filter                                 | Only templates with this name appear                   |
+------------------------------------------------------------+--------------------------------------------------------+
| Clear the filter                                           | All templates appear                                   |
+------------------------------------------------------------+--------------------------------------------------------+
| Click the ``Show`` icon                                    | The template content is displayed                      |
+------------------------------------------------------------+--------------------------------------------------------+
| Expand some of the entities, relationships and scenarios   | The details are displayed                              |
+------------------------------------------------------------+--------------------------------------------------------+
| Switch to ``Yaml View``                                    | A json representation is displayed                     |
+------------------------------------------------------------+--------------------------------------------------------+
| Switch back to ``Simple View``                             | The simple view is displayed                           |
+------------------------------------------------------------+--------------------------------------------------------+
+------------------------------------------------------------+--------------------------------------------------------+

Template View for admin
~~~~~~~~~~~~~~~~~~~~~~~
+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| Open the ``Template`` view under ``Admin->Vitrage`` and do |                                                        |
| the same checks as for tenant                              |                                                        |
+------------------------------------------------------------+--------------------------------------------------------+
| Delete all existing templates                              | Templates are deleted, the list is empty               |
+------------------------------------------------------------+--------------------------------------------------------+
| Click ``Add template`` and add v1_template.yaml. In the    | ERROR: A template definition can not contain includes  |
| ``Type`` drop-down, select ``definition``                  | or scenarios blocks                                    |
+------------------------------------------------------------+--------------------------------------------------------+
| Click ``Add template`` and add v1_template.yaml. In the    | The template is added with status ``ACTIVE``           |
| ``Type`` drop-down, select ``standard``                    |                                                        |
+------------------------------------------------------------+--------------------------------------------------------+
| Click ``Add template`` and add v2_definition_template.yaml | The template is added with status ``ACTIVE``           |
+------------------------------------------------------------+--------------------------------------------------------+
| Click ``Add template`` and add v2_equivalence.yaml         | The template is added with status ``ACTIVE`` and       |
|                                                            | and details ``No Validation``                          |
+------------------------------------------------------------+--------------------------------------------------------+
| Click ``Show`` icon for templates of types standard (v1,   | All templates are displayed correctly                  |
| v2 and v3), equivalence and definition                     |                                                        |
+------------------------------------------------------------+--------------------------------------------------------+
| Click ``Add template`` and add v2_wrong.yaml               | ERROR: Action definition must contain action_target    |
|                                                            | field. The template is not added.                      |
+------------------------------------------------------------+--------------------------------------------------------+

Templates with parameters
~~~~~~~~~~~~~~~~~~~~~~~~~
+------------------------------------------------------------+--------------------------------------------------------+
| What to execute                                            | Expected results                                       |
+============================================================+========================================================+
| Click ``Add template`` and add v2_with_params.yaml         | Error: Failed to resolve parameter - alarm_type        |
|                                                            | The template is not added.                             |
+------------------------------------------------------------+--------------------------------------------------------+
| Click ``Add template`` and add v2_with_params.yaml. Add    | Error: Failed to resolve parameter - alarm_name        |
| parameter alarm_type.                                      | The template is not added.                             |
+------------------------------------------------------------+--------------------------------------------------------+
| Click ``Add template`` and add v2_with_params.yaml. Add    | The template is added with status ``ACTIVE``           |
| parameters alarm_type, alarm_name, template_name and       |                                                        |
| new_state. Add and remove another parameter before         |                                                        |
| clicking Done.                                             |                                                        |
+------------------------------------------------------------+--------------------------------------------------------+
| Click the ``Show`` icon                                    | There is no ``parameters`` section. All parameters are |
|                                                            | resolved with the given values.                        |
+------------------------------------------------------------+--------------------------------------------------------+
| Click ``Add template`` and add v2_with_params.yaml. Add    | The template is added with status ``ACTIVE``           |
| parameters alarm_type and alarm_name only                  |                                                        |
+------------------------------------------------------------+--------------------------------------------------------+
| Click the ``Show`` icon                                    | There is no ``parameters`` section. alarm_type and     |
|                                                            | alarm_name parameters are resolved with the given      |
|                                                            | values. new_state has default value of ERROR.          |
+------------------------------------------------------------+--------------------------------------------------------+
| Perform similar tests for v3_with_params.yaml              |                                                        |
+------------------------------------------------------------+--------------------------------------------------------+
| Click ``Add template`` and add v3_with_default_params.yaml | The template is added with status ``ACTIVE``           |
+------------------------------------------------------------+--------------------------------------------------------+
