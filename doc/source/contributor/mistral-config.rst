=====================
Mistral Configuration
=====================

Vitrage can be configured to execute Mistral (the OpenStack Workflow service)
workflows based on certain topology or alarm conditions.


Enable Mistral Workflow Execution
---------------------------------

To enable Mistral workflow execution, add mistral to the list of notifiers in
/etc/vitrage/vitrage.conf file:

   .. code::

    [DEFAULT]
    notifiers = mistral


Add execute_mistral action
--------------------------

To execute a Mistral workflow under a certain condition, add an
'execute_mistral' action to a template file:

   .. code:: yaml

    scenarios:
      - condition: host_down_alarm [on] host
        actions:
          - execute_mistral:
             workflow: evacuate_host      # mandatory. The name of the workflow to be executed
             input:
               host_name: host1      # optional. A list of properties to be passed to the workflow
