============================
Enabling Vitrage in DevStack
============================

1. Download DevStack:

.. code:: bash

    git clone https://opendev.org/openstack-dev/devstack.git
    cd devstack

2. Add this repo as an external repository in ``local.conf`` file:

.. code:: bash

    [[local|localrc]]
    enable_plugin vitrage https://opendev.org/openstack/vitrage

3. Add this to add notification from nova to vitrage

.. code:: bash

   [[post-config|$NOVA_CONF]]
   [DEFAULT]
   notification_topics = notifications,vitrage_notifications
   notification_driver = messagingv2

   [notifications]
   versioned_notifications_topics = versioned_notifications,vitrage_notifications
   notification_driver = messagingv2
   notification_format = both

4. Add this to add notification from neutron to vitrage
   (make sure neutron is enabled in devstack)

.. code:: bash

   [[post-config|$NEUTRON_CONF]]
   [DEFAULT]
   notification_topics = notifications,vitrage_notifications
   notification_driver = messagingv2

5. Add this to add notification from cinder to vitrage

.. code:: bash

   [[post-config|$CINDER_CONF]]
   [DEFAULT]
   notification_topics = notifications,vitrage_notifications
   notification_driver = messagingv2

6. Add this to add notification from heat to vitrage and change default policy

.. code:: bash

   [[post-config|$HEAT_CONF]]
   [DEFAULT]
   notification_topics = notifications,vitrage_notifications
   notification_driver = messagingv2
   policy_file = /etc/heat/policy.yaml

7. Add this to add notification from aodh to vitrage

.. code:: bash

   [[post-config|$AODH_CONF]]
   [oslo_messaging_notifications]
   driver = messagingv2
   topics = notifications,vitrage_notifications

8. Run ``./stack.sh``
