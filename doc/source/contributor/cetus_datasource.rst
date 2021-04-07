================
Cetus Datasource
================

Cetus is a self-developed openstack solution of multi-k8s-clusters on openstack.
The datasource allow user to intergrate cluster and pod resources and topology into Vitrage.
The datasource provides how to get the Service-Endpoint-Url for self-developed internal projects based on openstack when
there is no client library for this project.

Note that currently we support only deploying multiple k8s clusters on nova.instance (nodes must be vm or bm instance).

Datasource configuration
------------------------

1. Add cetus to list of datasources in ``/etc/vitrage/vitrage.conf``

.. code::

    [datasources]
    types = ...,cetus.cluster,cetus.pod

2. Modify and Get the Service-Endpoint-Url of the self-developed module based on openstack in ``cetus_driver_base.py``

.. code::

    def _get_cetus_url(service_name='cetusv1'):
       pass

**Note:** It is recommended to customize this method to get the Service-Url.

3. Restart vitrage service in devstack/openstack

