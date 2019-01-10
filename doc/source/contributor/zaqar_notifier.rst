===================
Zaqar Configuration
===================

Vitrage can be configured to notify raised or cleared alarms to Zaqar (the OpenStack Messaging service)


Enable Zaqar Notifier
---------------------

To enable Zaqar notifier, add zaqar to the list of notifiers and add the zaqar queue in
/etc/vitrage/vitrage.conf file:

   .. code::

    [DEFAULT]
    notifiers = zaqar

    [zaqar]
    queue = <zaqar queue name to post the message>

