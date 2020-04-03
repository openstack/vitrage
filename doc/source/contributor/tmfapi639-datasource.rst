TMF API 639 - Vitrage
=====================

This datasource loads to Vitrage topologies exposed in TMF API 639 Resource Inventory Management.
https://www.tmforum.org/resources/specification/tmf639-resource-inventory-management-api-rest-specification-r17-0-1/

The fields used to define the topology will be:
- id
- name
- @type
- resourceRelationship : [resource: id]

Configuration
-------------


1. Create file ``tmfapi639_conf.yaml`` on your vitrage folder (generally: /etc/vitrage/) according to the following template:


      | -endpoint:
      |     snapshot: URL CONTAINING COMPLETE TOPOLOGY
      |     update: OPTIONAL URL CONTAINING NOTIFICATIONS FOR TOPOLOGY CHANGES 

You may allow as many endpoints as you desire.


2. Add tmfapi639 to list of datasources in ``/etc/vitrage/vitrage.conf``

.. code::

    [datasources]
    types = ...,tmfapi639,...


3. Restart vitrage service in devstack/openstack

**Warning:** due to limitations on TMF API definition, topology changes will require all parents all the way to the root to be defined in order to be correctly represented.
