..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.


Vitrage API
-----------
|

.. contents:: Contents:
   :local:

Overview
********
**This document describes the Vitrage API v1.**

**The Vitrage API provides a RESTful JSON interface for interacting with Vitrage Service.**

List Versions
^^^^^^^^^^^^^

Lists the supported versions of the Vitrage API.

GET /
~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json

Path Parameters
===============

None.

Query Parameters
================

None.

Request Body
============

None.

Request Examples
================

::

    GET / HTTP/1.1
    Host: 135.248.19.18:8999
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7
    Accept: application/json



ResponseStatus code
===================

-  200 - OK

Response Body
=============

Returns a JSON object with a 'links' array of links of supported versions.

Response Examples
=================

::

    {
        "versions": [
            {
               "id": "v1.0",
              "links": [
                    {
                     "href": "http://135.248.19.18:8999/v1/",
                    "rel": "self"
                   }
              ],
              "status": "CURRENT",
              "updated": "2015-11-29"
            }
        ]

    }



Get  topology
^^^^^^^^^^^^^

Get the topology for the cluster.
Its possible to filter the edges vertices and depth of the
graph


POST /v1/topology/
~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json

Path Parameters
===============

None.

Query Parameters
================

None

Request Body
============

Consists of a topology request definition which has the following properties:

* root - (string, optional) the root node to start. defaults to the openstack node
* depth - (int, optional) the depth of the topology graph. defaults to max depth
* graph_type-(string, optional) can be either tree or graph. defaults to graph
* query - (string, optional) a json query filter to filter the graph components. defaults to return all the graph
* all_tenants - (boolean, optional) shows the entities of all the tenants in the graph (in case the user has the permissions).

.. note:: **parameter graph_type=graph with depth parameter requires root parameter**

query expression
================
::

 query := expression
 expression := simple_expression|complex_expression
 simple_expression := {simple_operator: {field_name: value}}
 simple_operator := == | != | < | <= | > | >=
 complex_expression := {complex_operator: [expression, expression, ...]} | not_expression
 not_expression := {not: expression}
 complex_operator := and | or


Query example
=============

::

    POST /v1/topology/
    Host: 135.248.19.18:8999
    Content-Type: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

    {
        "query" :"
         {
            \"or\": [
              {
                \"==\": {
                  \"vitrage_type\": \"nova.host\"
                }
              },
              {
                \"==\": {
                  \"vitrage_type\": \"nova.instance\"
                }
              },
              {
                \"==\": {
                  \"vitrage_type\": \"nova.zone\"
                }
              },
              {
                \"==\": {
                  \"vitrage_type\": \"openstack.cluster\"
                }
              }
            ]

         }",
         "graph_type" : "tree"
     }

Response Status Code
====================

-  200 - OK
-  403 - Forbidden
-  404 - Not Found

Response Body
=============

Returns a JSON object that describes a graph with nodes
and links. If a tree representation is asked then returns
a Json tree with nodes and children.

An error of cannot represent as a tree will be return if the
graph is not a tree. (400 - Bad request)

Response Examples
=================

::

     {
       "vitrage_id": "96f6a30a-51eb-4e71-ae4a-0703b21ffa98",
       "name": "openstack.cluster",
       "graph_index": 0,
       "vitrage_category": "RESOURCE",
       "vitrage_operational_state": "OK",
       "state": "available",
       "vitrage_type": "openstack.cluster",
       "vitrage_sample_timestamp": "2018-06-11 08:43:33.757864+00:00",
       "vitrage_aggregated_state": "AVAILABLE",
       "vitrage_is_placeholder": false,
       "id": "OpenStack Cluster",
       "is_real_vitrage_id": true,
       "vitrage_is_deleted": false,
       "children": [
        {
          "vitrage_id": "12b11320-a6de-4ce5-892f-78fb1fa6bfef",
          "name": "nova",
          "update_timestamp": "2018-06-11 08:43:33.757864+00:00",
          "vitrage_category": "RESOURCE",
          "vitrage_operational_state": "OK",
          "state": "available",
          "vitrage_type": "nova.zone",
          "vitrage_sample_timestamp": "2018-06-11 08:43:33.757864+00:00",
          "graph_index": 1,
          "vitrage_aggregated_state": "AVAILABLE",
          "vitrage_is_placeholder": false,
          "id": "nova",
          "is_real_vitrage_id": true,
          "vitrage_is_deleted": false,
          "children": [
            {
              "vitrage_id": "5f9893b8-c622-4cb8-912d-534980f4e4f9",
              "name": "devstack-rocky-8",
              "update_timestamp": "2018-06-11 08:43:33.518059+00:00",
              "vitrage_category": "RESOURCE",
              "vitrage_operational_state": "OK",
              "state": "available",
              "vitrage_type": "nova.host",
              "vitrage_sample_timestamp": "2018-06-11 08:43:33.757864+00:00",
              "graph_index": 2,
              "vitrage_aggregated_state": "AVAILABLE",
              "vitrage_is_placeholder": false,
              "id": "devstack-rocky-8",
              "is_real_vitrage_id": true,
              "vitrage_is_deleted": false,
              "children": [
                {
                  "vitrage_id": "c90cc1dd-409c-4354-92f8-79b993e584c0",
                  "vitrage_is_deleted": false,
                  "graph_index": 3,
                  "vitrage_category": "RESOURCE",
                  "vitrage_operational_state": "N/A",
                  "vitrage_type": "nova.instance",
                  "vitrage_sample_timestamp": "2018-06-11 08:33:33.457974+00:00",
                  "vitrage_aggregated_state": null,
                  "vitrage_is_placeholder": true,
                  "id": "ce173654-c70d-4514-a3e9-1f9dd5c09dd8",
                  "is_real_vitrage_id": true
                },
                {
                  "vitrage_id": "94060508-5fea-4927-9a53-2b66864ab883",
                  "vitrage_is_deleted": false,
                  "graph_index": 4,
                  "vitrage_category": "RESOURCE",
                  "vitrage_operational_state": "N/A",
                  "vitrage_type": "nova.instance",
                  "vitrage_sample_timestamp": "2018-06-11 08:33:33.457992+00:00",
                  "vitrage_aggregated_state": null,
                  "vitrage_is_placeholder": true,
                  "id": "3af9a215-e109-476a-aa55-6868990684e4",
                  "is_real_vitrage_id": true
                },
                {
                  "vitrage_id": "ae0886d8-ee90-41df-a80a-006fdb80105b",
                  "graph_index": 5,
                  "name": "vm-4",
                  "update_timestamp": "2018-06-11 08:43:34.421455+00:00",
                  "vitrage_category": "RESOURCE",
                  "vitrage_operational_state": "OK",
                  "state": "ACTIVE",
                  "vitrage_type": "nova.instance",
                  "vitrage_sample_timestamp": "2018-06-11 08:43:34.421455+00:00",
                  "host_id": "devstack-rocky-8",
                  "vitrage_aggregated_state": "ACTIVE",
                  "vitrage_is_placeholder": false,
                  "project_id": "aa792cde038b41858a0f1bcf8f9b092d",
                  "id": "1233e48c-62ee-470e-8d4a-adff30211b5d",
                  "is_real_vitrage_id": true,
                  "vitrage_is_deleted": false
                },
                {
                  "vitrage_id": "4d197913-0687-4300-afb7-7fd331d35cff",
                  "graph_index": 6,
                  "name": "vm-3",
                  "update_timestamp": "2018-06-11 08:43:34.421490+00:00",
                  "vitrage_category": "RESOURCE",
                  "vitrage_operational_state": "OK",
                  "state": "ACTIVE",
                  "vitrage_type": "nova.instance",
                  "vitrage_sample_timestamp": "2018-06-11 08:47:24.137324+00:00",
                  "host_id": "devstack-rocky-8",
                  "vitrage_aggregated_state": "ACTIVE",
                  "vitrage_is_placeholder": false,
                  "project_id": "aa792cde038b41858a0f1bcf8f9b092d",
                  "id": "12cc6d3e-f801-4422-b2a0-43cedacb4eb5",
                  "is_real_vitrage_id": true,
                  "vitrage_is_deleted": false
                }
              ]
            }
          ]
        }
      ]
    }

Show RCA
^^^^^^^^

Shows the root cause analysis on an alarm.

GET /v1/rca/
~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json

Path Parameters
===============

None.

Query Parameters
================

- alarm id - (string(255)) get rca on this alarm.
- all_tenants - (boolean, optional) shows the rca of all tenants (in case the user has the permissions).

Request Body
============

None.

Request Examples
================

::

    GET /v1/rca/alarm_id=ALARM%3Anagios%3Ahost0%3ACPU%20load HTTP/1.1
    Host: 135.248.19.18:8999
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7
    Accept: application/json



Response Status code
====================

-  200 - OK

Response Body
=============

Returns a JSON object represented as a graph with all the alarms that either causing the alarm or caused by the requested alarm.

Response Examples
=================

::

 {
  "directed": true,
  "graph": {

  },
  "nodes": [
    {
      "vitrage_category": "ALARM",
      "vitrage_type": "nagios",
      "name": "CPU load",
      "state": "Active",
      "severity": "WARNING",
      "update_timestamp": "2015-12-01T12:46:41Z",
      "info": "WARNING - 15min load 1.66 at 32 CPUs",
      "resource_type": "nova.host",
      "resource_name": "host-0",
      "resource_id": "host-0",
      "id": 0,
      "vitrage_id": "a2760124-a174-46a1-926f-0d0d12a94a20"
    },
    {
      "vitrage_category": "ALARM",
      "vitrage_type": "vitrage",
      "name": "Machine Suboptimal",
      "state": "Active",
      "severity": "WARNING",
      "update_timestamp": "2015-12-01T12:46:41Z",
      "resource_type": "nova.instance",
      "resource_name": "vm0",
      "resource_id": "20d12a8a-ea9a-89c6-5947-83bea959362e",
      "id": 1,
      "vitrage_id": "4c0a2724-edce-4125-a74c-bf74d4413967"
    },
    {
      "vitrage_category": "ALARM",
      "vitrage_type": "vitrage",
      "name": "Machine Suboptimal",
      "state": "Active",
      "severity": "WARNING",
      "update_timestamp": "2015-12-01T12:46:41Z",
      "resource_type": "nova.instance",
      "resource_name": "vm1",
      "resource_id": "275097cf-954e-8e24-b185-9514e24b8591",
      "id": 2,
      "vitrage_id": "625f2914-cb0e-453a-977a-900aa7756524"
    }
  ],
  "links": [
    {
      "source": 0,
      "target": 1,
      "relationship": "causes"
    },
    {
      "source": 0,
      "target": 2,
      "relationship": "causes"
    }
  ],
  "multigraph": false,
  "inspected_index": 0
 }


List Alarms
^^^^^^^^^^^

Shows the alarms on a resource or all alarms

GET /v1/alarm/
~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json

Path Parameters
===============

None.

Query Parameters
================

vitrage_id - (string(255)) get alarm on this resource can be 'all' for all alarms.

 Optional Parameters:

- limit - (int) maximum number of items to return, if limit=0 the method will return all matched items in alarms table.
- sort_by - (array of string(255)) array of attributes by which results should be sorted.
- sort_dirs - (array of string(255)) per-column array of sort_dirs,corresponding to sort_keys ('asc' or 'desc').
- filter_by - (array of string(255)) array of attributes by which results will be filtered
- filter_vals - (array of string(255)) per-column array of filter values corresponding to filter_by.
- next_page - (bool) if True will return next page when marker is given, if False will return previous page when marker is given, otherwise, returns first page if no marker was given.
- marker - ((string(255)) if None returns first page, else if vitrage_id is given and next_page is True, return next #limit results after marker, else, if next page is False, return #limit results before marker.
- all_tenants - (boolean, optional) shows the alarms of all tenants (in case the user has the permissions).

Request Body
============

None.

Request Examples
================

::

    GET /v1/alarm/?vitrage_id=all
    Host: 135.248.19.18:8999
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7
    Accept: application/json

Response Status code
====================

-  200 - OK

Response Body
=============

Returns a JSON object with all the alarms requested.

Response Examples
=================

::


  [
     {
       "vitrage_category": "ALARM",
       "vitrage_type": "nagios",
       "name": "CPU load",
       "state": "Active",
       "severity": "WARNING",
       "update_timestamp": "2015-12-01T12:46:41Z",
       "info": "WARNING - 15min load 1.66 at 32 CPUs",
       "resource_type": "nova.host",
       "resource_name": "host-0",
       "resource_id": "host-0",
       "id": 0,
       "vitrage_id": "517bf941-0bec-4f7c-9870-8b79fc5086d1",
       "normalized_severity": "WARNING"
     },
     {
       "vitrage_category": "ALARM",
       "vitrage_type": "vitrage",
       "name": "Machine Suboptimal",
       "state": "Active",
       "severity": "CRITICAL",
       "update_timestamp": "2015-12-01T12:46:41Z",
       "resource_type": "nova.instance",
       "resource_name": "vm0",
       "resource_id": "20d12a8a-ea9a-89c6-5947-83bea959362e",
       "id": 1,
       "vitrage_id": "3e9f8ca2-1562-4ff8-be08-93427f5328f6",
       "normalized_severity": "CRITICAL"
     },
     {
       "vitrage_category": "ALARM",
       "vitrage_type": "vitrage",
       "name": "Machine Suboptimal",
       "state": "Active",
       "severity": "CRITICAL",
       "update_timestamp": "2015-12-01T12:46:41Z",
       "resource_type": "nova.instance",
       "resource_name": "vm1",
       "resource_id": "275097cf-954e-8e24-b185-9514e24b8591",
       "id": 2,
       "vitrage_id": "0320ba74-ab51-42e8-b60f-525b0ee63da4",
       "normalized_severity": "CRITICAL"
     },
     {
       "vitrage_category": "ALARM",
       "vitrage_type": "aodh",
       "name": "Memory overload",
       "state": "Active",
       "severity": "WARNING",
       "update_timestamp": "2015-12-01T12:46:41Z",
       "info": "WARNING - 15min load 1.66 at 32 CPUs",
       "resource_type": "nova.host",
       "resource_name": "host-0",
       "resource_id": "host-0",
       "id": 3,
       "vitrage_id": "4ee7916d-f8e7-4364-83b0-a7d1fe6ce8c3",
       "normalized_severity": "WARNING"
     }
 ]


Show alarm
^^^^^^^^^^
Show details of the specified alarm.

GET /v1/alarm/[vitrage_id]
~~~~~~~~~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)
-  Content-Type (String): application/json

Path Parameters
===============

- vitrage_id.

Query Parameters
================

None.

Request Body
============

None.

Request Examples
================

::

    GET /v1/alarm/7cfed44c-52cc-4097-931f-8fbec7410c5c
    Host: 127.0.0.1:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

Response Status code
====================

-  200 - OK
-  404 - Bad request

Response Body
=============

Returns details of the requested alarm.

Response Examples
=================

::

    {
      "vitrage_id": "019912c4-89e0-4d39-9836-237364cf6967",
      "vitrage_is_deleted": false,
      "severity": "critical",
      "update_timestamp": "2018-01-03T07:52:06Z",
      "resource_id": "82ea32a3-528b-4836-bfdb-3f17acd2f640",
      "vitrage_category": "ALARM",
      "state": "Active",
      "vitrage_type": "vitrage",
      "vitrage_sample_timestamp": "2018-01-03 07:52:06.497732+00:00",
      "vitrage_operational_severity": "CRITICAL",
      "vitrage_is_placeholder": false,
      "vitrage_aggregated_severity": "CRITICAL",
      "vitrage_resource_id": "82ea32a3-528b-4836-bfdb-3f17acd2f640",
      "vitrage_resource_type": "nova.instance",
      "is_real_vitrage_id": true,
      "name": "deducy"
    }

Show Alarm Count
^^^^^^^^^^^^^^^^

Shows how many alarms of each operations severity exist

GET /v1/alarm/count
~~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token

Path Parameters
===============

None.

Query Parameters
================

- all_tenants - (boolean, optional) includes alarms of all tenants in the count (in case the user has the permissions).


Request Body
============

None.

Request Examples
================

::

    GET /v1/alarm/count/?all_tenants=True HTTP/1.1
    Host: 135.248.19.18:8999
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7
    Accept: application/json

Response Status code
====================

-  200 - OK

Response Body
=============

Returns a JSON object with all the alarms requested.

Response Examples
=================

::

   {
     "severe": 2,
     "critical": 1,
     "warning": 3,
     "na": 4,
     "ok": 5
   }


Template Validate
^^^^^^^^^^^^^^^^^

An API for validating templates

POST /v1/template/
~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)
-  Content-Type (String): application/json

Path Parameters
===============

None.

Query Parameters
================

None

Request Body
============

-  templates (string, required) - A list of the structured content of the template

Request Examples
================

::

    POST /v1/template
    Host: 135.248.18.122:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Content-Type: application/json
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

    {
        "templates": [
            ["tmp/templates/mem_decude_v3.yaml", {
                "metadata": {
                    "version": "3",
                    "name": "mem_decude_scenarios",
                    "type": "standard",
                    "description": "scenarios triggered by high mem load on physical"
                },
                "entities": {
                    "host_alarm": {
                        "category": "ALARM",
                        "name": "mem_utilization"
                    },
                    "instance_alarm": {
                        "category": "ALARM",
                        "type": "vitrage",
                        "severity": "CRITICAL",
                        "name": "mem_utilization by host mem"
                    },
                    "instance": {
                        "category": "RESOURCE",
                        "type": "nova.instance"
                    },
                    "host": {
                        "category": "RESOURCE",
                        "type": "nova.host"
                    }
                },
                "scenarios": [{
                    "condition": "host_alarm [on] host",
                    "actions": [{
                        "set_state": {
                            "state": "ERROR",
                            "target": "host"
                        }
                    }]
                }, {
                    "condition": "host_alarm [on] host AND host [contains] instance",
                    "actions": [{
                        "set_state": {
                            "state": "ERROR",
                            "target": "instance"
                        }
                    }, {
                        "raise_alarm": {
                            "target": "instance",
                            "alarm_name": "mem used_percent by host mem",
                            "severity": "WARNING",
                            "causing_alarm": "host_alarm"
                        }
                    }]
                }, {
                    "condition": "host_alarm [on] host AND instance_alarm [on] instance AND host [contains] instance",
                    "actions": [{
                        "add_causal_relationship": {
                            "source": "host_alarm",
                            "target": "instance_alarm"
                        }
                    }]
                }]
            }]
        ]
    }


Response Status code
====================

None

Response Body
=============

Returns a JSON object that is a list of results.
Each result describes a full validation (syntax and content) of one template file.

Response Examples
=================

::

    {
        "results": [{
            "file path": "tmp/templates/mem_decude_v3.yaml",
            "status": "validation OK",
            "description": "Template validation",
            "message": "Template validation is OK",
            "status code": 0
        }]
    }


Template List
^^^^^^^^^^^^^

List all templates in the database, both those that passed validation and those that did not.

GET /v1/template/
~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)

Path Parameters
===============

None

Query Parameters
================

None

Request Body
============

None

Request Examples
================

::

    GET /v1/template/
    Host: 135.248.18.122:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

Response Status code
====================

None

Response Body
=============

Returns list of all templates in the database with status ACTIVE or ERROR.

Response Examples
=================

::

  +--------------------------------------+-----------------------------------------+--------+---------------------------+---------------------+-------------+
  | UUID                                 | Name                                    | Status | Status details            | Date                | Type        |
  +--------------------------------------+-----------------------------------------+--------+---------------------------+---------------------+-------------+
  | ae3c0752-1df9-408c-89d5-8b32b86f403f | host_disk_io_overloaded_usage_scenarios | ACTIVE | Template validation is OK | 2018-01-23 10:14:05 | standard    |
  | f254edb0-53cb-4552-969b-bdad24a14a03 | ceph_health_is_not_ok_scenarios         | ACTIVE | Template validation is OK | 2018-01-23 10:20:29 | standard    |
  | bf405cfa-3f19-4761-9329-6e48f21cd466 | basic_def_template                      | ACTIVE | Template validation is OK | 2018-01-23 10:20:56 | definition  |
  | 7b5d6ca8-9ee0-4388-8c91-819b8786b78e | zabbix_host_equivalence                 | ACTIVE | No Validation             | 2018-01-23 10:21:13 | equivalence |
  +--------------------------------------+-----------------------------------------+--------+---------------------------+---------------------+-------------+

Template Show
^^^^^^^^^^^^^

Shows the template body for given template ID or Name

GET /v1/template/[id]
~~~~~~~~~~~~~~~~~~~~~

Headers
=======

-  User-Agent (string)
-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json

Path Parameters
===============

- template id or name

Query Parameters
================

None

Request Body
============

None

Request Examples
================

::

    GET /v1/template/a0bdb89a-fe4c-4b27-adc2-507b7ec44c24
    Host: 135.248.19.18:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7
    Accept: application/json



Response Status code
====================

-  200 - OK
-  404 - failed to show template with uuid: [template_uuid]

Response Body
=============

Returns a JSON object which represents the template body

Response Examples
=================

::

    {
      "scenarios": [
        {
          "scenario": {
            "actions": [
              {
                "action": {
                  "action_target": {
                    "target": "instance"
                  },
                  "properties": {
                    "alarm_name": "exploding_world",
                    "severity": "CRITICAL"
                  },
                  "action_type": "raise_alarm"
                }
              }
            ],
            "condition": "alarm_1_on_host and host_contains_instance"
          }
        },
        {
          "scenario": {
            "actions": [
              {
                "action": {
                  "action_target": {
                    "source": "alarm_1",
                    "target": "alarm_2"
                  },
                  "action_type": "add_causal_relationship"
                }
              }
            ],
            "condition": "alarm_1_on_host and alarm_2_on_instance and host_contains_instance"
          }
        }
      ],
      "definitions": {
        "relationships": [
          {
            "relationship": {
              "relationship_type": "on",
              "source": "alarm_1",
              "target": "host",
              "template_id": "alarm_1_on_host"
            }
          },
          {
            "relationship": {
              "relationship_type": "on",
              "source": "alarm_2",
              "target": "instance",
              "template_id": "alarm_2_on_instance"
            }
          },
          {
            "relationship": {
              "relationship_type": "contains",
              "source": "host",
              "target": "instance",
              "template_id": "host_contains_instance"
            }
          }
        ],
        "entities": [
          {
            "entity": {
              "vitrage_category": "ALARM",
              "vitrage_type": "nagios",
              "name": "check_libvirtd",
              "template_id": "alarm_1"
            }
          },
          {
            "entity": {
              "vitrage_category": "RESOURCE",
              "vitrage_type": "nova.host",
              "template_id": "host"
            }
          },
          {
            "entity": {
              "vitrage_category": "RESOURCE",
              "vitrage_type": "nova.instance",
              "template_id": "instance"
            }
          },
          {
            "entity": {
              "vitrage_category": "ALARM",
              "vitrage_type": "vitrage",
              "name": "exploding_world",
              "template_id": "alarm_2"
            }
          }
        ]
      },
      "metadata": {
        "name": "first_deduced_alarm_ever"
    }


PUT /v1/template/
~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)

Path Parameters
===============

None

Query Parameters
================

None

Request Body
============

-  templates (string, required) - A list of the structured content of the template
-  template_type (string, required) - template type (standard, None)
-  overwrite (boolean, optional) - if template already exists will overwrite it

Request Examples
================

::

    PUT /v1/template/
    Host: 135.248.18.122:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

    {
        "template_type": "standard",
        "templates": [
            ["tmp/templates/mem_decude_v3.yaml", {
                "metadata": {
                    "version": "3",
                    "name": "mem_decude_scenarios",
                    "type": "standard",
                    "description": "scenarios triggered by high mem load on physical"
                },
                "entities": {
                    "host_alarm": {
                        "category": "ALARM",
                        "name": "mem_utilization"
                    },
                    "instance_alarm": {
                        "category": "ALARM",
                        "type": "vitrage",
                        "severity": "CRITICAL",
                        "name": "mem_utilization by host mem"
                    },
                    "instance": {
                        "category": "RESOURCE",
                        "type": "nova.instance"
                    },
                    "host": {
                        "category": "RESOURCE",
                        "type": "nova.host"
                    }
                },
                "scenarios": [{
                    "condition": "host_alarm [on] host",
                    "actions": [{
                        "set_state": {
                            "state": "ERROR",
                            "target": "host"
                        }
                    }]
                }, {
                    "condition": "host_alarm [on] host AND host [contains] instance",
                    "actions": [{
                        "set_state": {
                            "state": "ERROR",
                            "target": "instance"
                        }
                    }, {
                        "raise_alarm": {
                            "target": "instance",
                            "alarm_name": "mem used_percent by host mem",
                            "severity": "WARNING",
                            "causing_alarm": "host_alarm"
                        }
                    }]
                }, {
                    "condition": "host_alarm [on] host AND instance_alarm [on] instance AND host [contains] instance",
                    "actions": [{
                        "add_causal_relationship": {
                            "source": "host_alarm",
                            "target": "instance_alarm"
                        }
                    }]
                }]
            }]
        ]
    }



Response Status code
====================

None

Response Body
=============

Returns list of all added templates.
In case of duplicate templates returns info message.

Response Examples
=================

::


   +--------------------------------------+----------------------------------+---------+---------------------------+----------------------------+----------+
   | UUID                                 | Name                             | Status  | Status details            | Date                       | Type     |
   +--------------------------------------+----------------------------------+---------+---------------------------+----------------------------+----------+
   | d661a9b1-87b5-4b2e-933f-043b19a39d17 | mem_decude_scenarios | LOADING | Template validation is OK | 2018-01-23 18:55:54.472329 | standard |
   +--------------------------------------+----------------------------------+---------+---------------------------+----------------------------+----------+



DELETE /v1/template/
~~~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)

Path Parameters
===============

None

Query Parameters
================

id - (string(255),or uuid)  template id

Request Body
============

None

Request Examples
================

::

    DELETE /v1/template/?id=76515dbe-2256-4693-974d-483232b7d79a
    Host: 135.248.18.122:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Accept: string
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

Response Status code
====================

200 - OK

Response Body
=============

None

Response Examples
=================

None


Event Post
^^^^^^^^^^
Post an event to Vitrage message queue, to be consumed by a datasource driver.

POST /v1/event/
~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)
-  Content-Type (String): application/json

Path Parameters
===============

None.

Query Parameters
================

None.

Request Body
============

An event to be posted. Will contain the following fields:

- time: a timestamp of the event. In case of a monitor event, should specify when the fault has occurred.
- type: the type of the event.
- details: a key-value map of metadata.

A dict of some potential details, copied from the Doctor SB API reference:

- hostname: the hostname on which the event occurred.
- source: the display name of reporter of this event. This is not limited to monitor, other entity can be specified such as 'KVM'.
- cause: description of the cause of this event which could be different from the type of this event.
- severity: the severity of this event set by the monitor.
- status: the status of target object in which error occurred.
- monitorID: the ID of the monitor sending this event.
- monitorEventID: the ID of the event in the monitor. This can be used by operator while tracking the monitor log.
- relatedTo: the array of IDs which related to this event.

Request Examples
================

::

    POST /v1/event/
    Host: 135.248.18.122:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Content-Type: application/json
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7


::

    {
        'time': '2016-04-12T08:00:00',
        'type': 'compute.host.down',
        'details': {
            'hostname': 'compute-1',
            'source': 'sample_monitor',
            'cause': 'link-down',
            'severity': 'critical',
            'status': 'down',
            'monitor_id': 'monitor-1',
            'monitor_event_id': '123',
        }
    }



Response Status code
====================

-  200 - OK
-  404 - Not Found

Response Body
=============

Returns an empty response body if the request was OK.
Otherwise returns a detailed error message (e.g. 'missing time parameter').

Resource list
^^^^^^^^^^^^^
List the resources with specified type or all the resources.

POST /v1/resources/
~~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)
-  Content-Type (String): application/json

Path Parameters
===============

None.

Query Parameters
================

None.

Request Body
============

* resource_type - (string, optional) the type of resource, defaults to return all resources.
* all_tenants - (boolean, optional) shows the resources of all tenants (in case the user has the permissions).
* query - (string, optional) a json query to filter the resources by

Request Examples
================

::

    POST /v1/resources/
    Host: 135.248.18.122:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Content-Type: application/json
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7


Response Status code
====================

-  200 - OK
-  404 - Bad request

Query example
=============

::

    POST /v1/resources/
    Host: 135.248.19.18:8999
    Content-Type: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

    {
        "query" :"
         {
            \"or\": [
              {
                \"==\": {
                  \"state\": \"OK\"
                }
              },
              {
                \"==\": {
                  \"state\": \"SUBOPTIMAL\"
                }
              }
            ]

         }",
         "resource_type" : "nova.host"
         "all_tenants" : True
     }

Response Body
=============

Returns a list with all the resources requested.

Response Examples
=================

::

  [
    {
      "vitrage_id": "6b4a4272-0fef-4b35-9c3c-98bc8e71cd38",
      "vitrage_aggregated_state": "AVAILABLE",
      "state": "available",
      "vitrage_type": "nova.host",
      "id": "cloud",
      "metadata": {
        "name": "cloud",
        "update_timestamp": "2017-04-24 04:27:47.501777+00:00"
      }
    }
  ]


Resource show
^^^^^^^^^^^^^
Show the details of specified resource.

GET /v1/resources/[vitrage_id]
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)
-  Content-Type (String): application/json

Path Parameters
===============

- vitrage_id.

Query Parameters
================

None.

Request Body
============

None.

Request Examples
================

::

    GET /v1/resources/`<vitrage_id>`
    Host: 127.0.0.1:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

Response Status code
====================

-  200 - OK
-  404 - Bad request

Response Body
=============

Returns details of the requested resource.

Response Examples
=================

::

    {
      "vitrage_category": "RESOURCE",
      "vitrage_is_placeholder": false,
      "vitrage_is_deleted": false,
      "name": "vm-1",
      "update_timestamp": "2015-12-01T12:46:41Z",
      "state": "ACTIVE",
      "project_id": "0683517e1e354d2ba25cba6937f44e79",
      "vitrage_type": "nova.instance",
      "id": "dc35fa2f-4515-1653-ef6b-03b471bb395b",
      "vitrage_id": "11680c27-86a2-41a7-89db-863e68b1c2c9"
    }

Resource count
^^^^^^^^^^^^^^
Count resources

POST /v1/resources/count
~~~~~~~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)
-  Content-Type (String): application/json

Path Parameters
===============

None.

Query Parameters
================

None.

Request Body
============

* resource_type - (string, optional) the type of resource, defaults to return all resources.
* all_tenants - (boolean, optional) shows the resources of all tenants (in case the user has the permissions).
* query - (string, optional) a json query to filter the resources by
* group_by - (string, optional) a resource data field, to group by its values

Request Examples
================

::

    POST /v1/resources/count/
    Host: 127.0.0.1:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7


Response Status code
====================

-  200 - OK
-  404 - Bad request

Response Body
=============

Returns counts of the requested resource, grouped by the selected field

Query example
=============

::

    POST /v1/resources/count/
    Host: 135.248.19.18:8999
    Content-Type: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

    {
        "query" :"
         {
            \"or\": [
              {
                \"==\": {
                  \"state\": \"OK\"
                }
              },
              {
                \"==\": {
                  \"state\": \"SUBOPTIMAL\"
                }
              }
            ]

         }",
         "group_by" : "vitrage_operational_status",
         "resource_type" : "nova.instance"
         "all_tenants" : True
     }


Response Examples
=================

For the above request, will count all instances with status OK or SUBOPTIMAL,
group by the status field.

::

    {
      "OK": 157,
      "SUBOPTIMAL": 3,
    }

Webhook List
^^^^^^^^^^^^
List all webhooks.

GET /v1/webhook/
~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)
-  Content-Type (String): application/json

Path Parameters
===============

None.

Query Parameters
================

None.

Request Body
============

None.

Request Examples
================

::

    GET /v1/webhook
    Host: 135.248.18.122:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Content-Type: application/json
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7


Response Status code
====================

-  200 - OK
-  404 - Bad request

Response Body
=============

Returns a list with all webhooks.

Response Examples
=================

::

  [
   {
      "url":"https://requestb.in/tq3fkvtq",
      "headers":"{'content-type': 'application/json'}",
      "regex_filter":"{'name':'e2e.*'}",
      "created_at":"2018-01-04T12:27:47.000000",
      "id":"c35caf11-f34d-440e-a804-0c1a4fdfb95b"
   }
  ]

Webhook Show
^^^^^^^^^^^^
Show the details of specified webhook.

GET /v1/webhook/[id]
~~~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)
-  Content-Type (String): application/json

Path Parameters
===============

- id.

Query Parameters
================

None.

Request Body
============

None.

Request Examples
================

::

    GET /v1/resources/`<id>`
    Host: 127.0.0.1:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

Response Status code
====================

-  200 - OK
-  404 - Bad request

Response Body
=============

Returns details of the requested webhook.

Response Examples
=================

::

   {
      "url":"https://requestb.in/tq3fkvtq",
      "created_at":"2018-01-04T12:27:47.000000",
      "updated_at":null,
      "id":"c35caf11-f34d-440e-a804-0c1a4fdfb95b",
      "headers":"{'content-type': 'application/json'}",
      "regex_filter":"{'name':'e2e.*'}"
   }

Webhook Add
^^^^^^^^^^^
Add a webhook to the database, to be used by the notifier.

POST /v1/webhook/
~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)
-  Content-Type (String): application/json

Path Parameters
===============

None.

Query Parameters
================

None.

Request Body
============

A webhook to be added. Will contain the following fields:

+------------------+-----------------------------------------------------------------+--------------+
| Name             | Description                                                     | Required     |
+==================+=================================================================+==============+
| url              | The webhook URL to which notifications will be sent             | Yes          |
+------------------+-----------------------------------------------------------------+--------------+
| regex_filter     | A JSON string to filter for specific events                     | No           |
+------------------+-----------------------------------------------------------------+--------------+
| headers          | A JSON string specifying additional headers to the notification | No           |
+------------------+-----------------------------------------------------------------+--------------+

- If no regex filter is supplied, all notifications will be sent.
- The defaults headers are : '{'content-type': 'application/json'}'

Request Examples
================

::

    POST /v1/webhook/
    Host: 135.248.18.122:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Content-Type: application/json
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7


::

   {
     "url":"https://requestb.in/tqfkvtqa",
     "headers":"",
     "regex_filter":"{'name':'e2e.*'}"
   }


Response Status code
====================

-  200 - OK
-  400 - Bad request

Response Body
=============

Returns webhook details if request was OK,
otherwise returns a detailed error message (e.g. 'headers in bad format').

Webhook Delete
^^^^^^^^^^^^^^
Delete a specified webhook.

DELETE /v1/webhook/[id]
~~~~~~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json
-  User-Agent (String)
-  Content-Type (String): application/json

Path Parameters
===============

- id.

Query Parameters
================

None.

Request Body
============

None.

Request Examples
================

::

    DELETE /v1/webhook/`<id>`
    Host: 127.0.0.1:8999
    User-Agent: keystoneauth1/2.3.0 python-requests/2.9.1 CPython/2.7.6
    Accept: application/json
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7

Response Status code
====================

-  200 - OK
-  404 - Bad request

Response Body
=============

Returns a success message if the webhook is deleted, otherwise an error
message is returned.


Service list
^^^^^^^^^^^^

Lists the vitrage services present in the system

GET  /v1/services/
~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json

Path Parameters
===============

None.

Query Parameters
================

None.

Request Body
============

None.

Request Examples
================

::

    GET /v1/service/ HTTP/1.1
    Host: 135.248.19.18:8999
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7
    Accept: application/json



ResponseStatus code
===================

-  200 - OK
-  404 - Not Found
-  500 - Service API not supported
-  500 - Failed to connect to coordination backend

Response Body
=============

Returns a JSON object with a list of all services.

Response Examples
=================

::

    [
      {
        "Created At": "2019-02-10T11:07:15+00:00",
        "Hostname": "controller-1",
        "Process Id": 23161,
        "Name": "ApiWorker worker(0)"
      },
      {
        "Created At": "2019-02-10T11:07:15+00:00",
        "Hostname": "controller-1",
        "Process Id": 23153,
        "Name": "EvaluatorWorker worker(0)"
      },
      {
        "Created At": "2019-02-10T11:07:15+00:00",
        "Hostname": "controller-1",
        "Process Id": 23155,
        "Name": "EvaluatorWorker worker(1)"
      },
      {
        "Created At": "2019-02-10T11:07:15+00:00",
        "Hostname": "controller-1",
        "Process Id": 23157,
        "Name": "EvaluatorWorker worker(2)"
      },
      {
        "Created At": "2019-02-10T11:07:15+00:00",
        "Hostname": "controller-1",
        "Process Id": 23158,
        "Name": "EvaluatorWorker worker(3)"
      },
      {
        "Created At": "2019-02-10T11:07:33+00:00",
        "Hostname": "controller-1",
        "Process Id": 23366,
        "Name": "MachineLearningService worker(0)"
      },
      {
        "Created At": "2019-02-10T11:07:35+00:00",
        "Hostname": "controller-1",
        "Process Id": 23475,
        "Name": "PersistorService worker(0)"
      },
      {
        "Created At": "2019-02-10T11:07:15+00:00",
        "Hostname": "controller-1",
        "Process Id": 23164,
        "Name": "SnmpParsingService worker(0)"
      },
      {
        "Created At": "2019-02-10T11:14:30+00:00",
        "Hostname": "controller-1",
        "Process Id": 25698,
        "Name": "VitrageApi"
      },
      {
        "Created At": "2019-02-10T11:14:30+00:00",
        "Hostname": "controller-1",
        "Process Id": 25699,
        "Name": "VitrageApi"
      },
      {
        "Created At": "2019-02-10T11:07:32+00:00",
        "Hostname": "controller-1",
        "Process Id": 23352,
        "Name": "VitrageNotifierService worker(0)"
      }
    ]

Template versions
^^^^^^^^^^^^^^^^^

Lists the vitrage template supported versions

GET  /v1/template/versions
~~~~~~~~~~~~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json

Path Parameters
===============

None.

Query Parameters
================

None.

Request Body
============

None.

Request Examples
================

::

    GET /v1/template/versions HTTP/1.1
    Host: 135.248.19.18:8999
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7
    Accept: application/json



ResponseStatus code
===================

-  200 - OK
-  404 - Not Found

Response Body
=============

Returns a JSON object with a list of all template version supported.

Response Examples
=================

::

    [
        {
            "version": "v1",
            "status": "SUPPORTED"
        },
        {
            "version": "v2",
            "status": "SUPPORTED"
        },
        {
            "version": "v3",
            "status": "CURRENT"
        }
    ]



Status
^^^^^^

prints the status of vitrage

GET  /v1/status
~~~~~~~~~~~~~~~

Headers
=======

-  X-Auth-Token (string, required) - Keystone auth token
-  Accept (string) - application/json

Path Parameters
===============

None.

Query Parameters
================

None.

Request Body
============

None.

Request Examples
================

::

    GET /v1/status HTTP/1.1
    Host: 135.248.19.18:8999
    X-Auth-Token: 2b8882ba2ec44295bf300aecb2caa4f7
    Accept: application/json



ResponseStatus code
===================

-  200 - OK
-  503 - Service Unavailable vitrage-graph is not ready
-  503 - Service Unavailable vitrage-graph is not available

Response Body
=============

Returns a JSON object with ok status
or 503 status code if not ok

Response Examples
=================

::

    {
        "reason": "OK"
    }

