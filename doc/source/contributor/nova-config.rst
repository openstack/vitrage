=============================
Nova Datasource Configuration
=============================

By default, Nova datasource listens to Nova versioned notifications. If you
are using Nova legacy notifications, then it should be indicated in Vitrage
configuration as well.

That is, if you have in ``/etc/nova/nova.conf`` or in ``/etc/nova/nova-cpu.conf``:

.. code:: bash

   notification_format = unversioned

Then you should set in ``/etc/vitrage/vitrage.conf``:

.. code:: bash

   [DEFAULT]
   use_nova_versioned_notifications = False


In other cases there is no need to set this option.
