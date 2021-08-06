.. _install-rdo:

Install and configure for Red Hat Enterprise Linux and CentOS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


This section describes how to install and configure the Root Cause Analysis service
for Red Hat Enterprise Linux 7 and CentOS 7.

Manual
++++++

Install Vitrage
---------------

Install Vitrage and python-vitrageclient
========================================
#. Install Vitrage:

.. code-block:: console

        $ sudo pip install vitrage

        $ sudo pip install python-vitrageclient

To install a specific version, add the version number:

.. code-block:: console

        $ sudo pip install vitrage==VITRAGE_VERSION

        $ sudo pip install python-vitrageclient==VITRAGE_CLIENT_VERSION


+------------------+-----------------+---------------+
| Release version  | Vitrage version | Client version|
+==================+=================+===============+
| Ocata            | 1.5.1           | 1.1.1         |
+------------------+-----------------+---------------+
| Pike             | 1.8.2           | 1.4.0         |
+------------------+-----------------+---------------+
| Queens           | ...             | ...           |
+------------------+-----------------+---------------+

Configure Vitrage
-----------------

Create the Vitrage folders
==========================
#. Create /etc/vitrage folder and sub folders, **with permission 755**:

.. code-block:: console

        $ mkdir /etc/vitrage
        $ chmod 755 /etc/vitrage

        $ mkdir /etc/vitrage/static_datasources
        $ chmod 755 /etc/vitrage/static_datasources

        $ sudo mkdir /var/log/vitrage
        $ sudo chmod 755 /var/log/vitrage

Copy `api-paste.ini`_ to /etc/vitrage/

Copy the `datasources_values`_ folder with its content under /etc/vitrage/

**Note:** You don't need to copy all files in this folder, only the ones that
belong to datasources you plan to use. The only file that **must** be copied
is vitrage.yaml



.. _api-paste.ini: https://opendev.org/openstack/vitrage/src/branch/master/etc/vitrage/api-paste.ini
.. _datasources_values: https://opendev.org/openstack/vitrage/src/branch/master/etc/vitrage/datasources_values

Create the vitrage.conf file
============================

Create /etc/vitrage/vitrage.conf file with the following information:

.. code:: bash

    [DEFAULT]
    # debug = False
    transport_url = <transport-url>
    # notifiers = nova

    [service_credentials]
    auth_url = http://<ip>:5000
    region_name = RegionOne
    project_name = admin
    password = <password>
    project_domain_id = default
    user_domain_id = default
    username = admin
    auth_type = password

    [keystone_authtoken]
    auth_uri = http://<ip>:5000
    project_domain_name = Default
    project_name = service
    user_domain_name = Default
    password = <password>
    username = vitrage
    auth_url = http://<ip>:5000
    auth_type = password

Replace **<ip>** with your controller node's IP.
Set the list of datasource you would like to use for Vitrage.

**Note:** In order for a datasource to be supported, the underlying component
(like Neutron, Heat, Zabbix, etc.) should be installed separately.

.. code:: bash

    [datasources]
    types = nova.host,nova.instance,nova.zone,static,aodh,cinder.volume,neutron.network,neutron.port,heat.stack,doctor

Configure notifications from other datasources
----------------------------------------------

Notifications from Aodh
=======================
In order to configure notifications from Aodh to Vitrage, set the following in
`/etc/aodh/aodh.conf`:

.. code:: bash

   [oslo_messaging_notifications]
   driver = messagingv2
   topics = notifications,vitrage_notifications


Notifications from other OpenStack components
=============================================

In order to configure notifications from OpenStack components (Nova, Cinder,
Neutron, Heat and Aodh) to Vitrage, set the following in their conf files:

.. code:: bash

   [DEFAULT]
   notification_topics = notifications,vitrage_notifications
   notification_driver=messagingv2


[notifications]
versioned_notifications_topics = versioned_notifications,vitrage_notifications
notification_driver = messagingv2

Initialize Vitrage
------------------

Create the Vitrage account
==========================

.. code:: bash

    openstack user create vitrage --password password --domain=Default
    openstack role add admin --user vitrage --project service
    openstack role add admin --user vitrage --project admin

Create the Vitrage endpoint
===========================

.. code:: bash

    openstack service create rca --name vitrage --description="Root Cause Analysis Service"
    openstack endpoint create vitrage --region <region> public http://<ip>:8999
    openstack endpoint create vitrage --region <region> internal http://<ip>:8999
    openstack endpoint create vitrage --region <region> admin http://<ip>:8999


Start the Vitrage Services
--------------------------

Run the following commands:

.. code:: bash

    vitrage-graph
    vitrage-api
    vitrage-notifier
    vitrage-persistor
    vitrage-ml


Install the Vitrage Dashboard
-----------------------------

Follow the vitrage-dashboard_ installation procedure.

.. _vitrage-dashboard: https://opendev.org/openstack/vitrage-dashboard/src/branch/master/doc/source/contributor/installation.rst

Automatic
+++++++++

Automatic installation for RDO is in progress; the patch can be found on the `RDO Gerrit`_

.. _`RDO Gerrit`: https://review.rdoproject.org/r/#/c/5962/
