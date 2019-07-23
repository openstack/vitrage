# Copyright 2016 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from oslo_utils import importutils as utils

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import UpdateMethod
from vitrage.datasources.nagios import NAGIOS_DATASOURCE
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources import utils as ds_utils
from vitrage.datasources.zabbix import ZABBIX_DATASOURCE
from vitrage.tests import base


ZABBIX_DATASOURCE_NONE = '_'.join((ZABBIX_DATASOURCE, UpdateMethod.NONE))
ZABBIX_DATASOURCE_PULL = '_'.join((ZABBIX_DATASOURCE, UpdateMethod.PULL))
ZABBIX_DATASOURCE_PUSH = ZABBIX_DATASOURCE
ZABBIX_DATASOURCE_PULL_NO_INTERVAL = \
    '_'.join((ZABBIX_DATASOURCE, UpdateMethod.PULL, 'no_interval'))


class DatasourceUpdateMethod(base.BaseTest):

    DATASOURCES_OPTS = [
        cfg.ListOpt('types',
                    default=[NOVA_HOST_DATASOURCE,
                             NOVA_INSTANCE_DATASOURCE,
                             NAGIOS_DATASOURCE,
                             ZABBIX_DATASOURCE_NONE,
                             ZABBIX_DATASOURCE_PULL,
                             ZABBIX_DATASOURCE_PUSH,
                             ZABBIX_DATASOURCE_PULL_NO_INTERVAL],
                    help='Names of supported data sources'),
        cfg.StrOpt('notification_topic',
                   default='vitrage_notifications',
                   help='Vitrage configured notifications topic')
    ]

    NOVA_HOST_OPTS = [
        cfg.StrOpt(DSOpts.DRIVER,
                   default='vitrage.datasources.nova.host.driver.HostDriver',
                   help='Nova host driver class path',
                   required=True),
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.NONE,
                   help='None: updates only via Vitrage periodic snapshots.'
                        'Pull: updates every [changes_interval] seconds.'
                        'Push: updates by getting notifications from the'
                        ' datasource itself.',
                   required=True),
    ]

    NOVA_INSTANCE_OPTS = [
        cfg.StrOpt(DSOpts.DRIVER,
                   default='vitrage.datasources.nova.instance.driver.'
                           'InstanceDriver',
                   help='Nova instance driver class path',
                   required=True),
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH,
                   required=True),
    ]

    NAGIOS_OPTS = [
        cfg.StrOpt(DSOpts.DRIVER,
                   default='vitrage.datasources.nagios.driver.NagiosDriver',
                   help='Nagios driver class path',
                   required=True),
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PULL,
                   required=True),
        cfg.IntOpt(DSOpts.CHANGES_INTERVAL,
                   default=30,
                   min=30,
                   help='interval between checking changes in nagios'
                        ' data source'),
    ]

    ZABBIX_OPTS_PUSH = [
        cfg.StrOpt(DSOpts.DRIVER,
                   default='vitrage.datasources.zabbix.driver.ZabbixDriver',
                   help='Zabbix driver class path',
                   required=True),
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PUSH,
                   required=True),
        cfg.IntOpt(DSOpts.CHANGES_INTERVAL,
                   default=30,
                   min=30,
                   help='interval between checking changes in zabbix'
                        ' data source'),
    ]

    ZABBIX_OPTS_PULL = [
        cfg.StrOpt(DSOpts.DRIVER,
                   default='vitrage.datasources.zabbix.driver.ZabbixDriver',
                   help='Zabbix driver class path',
                   required=True),
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PULL,
                   required=True),
        cfg.IntOpt(DSOpts.CHANGES_INTERVAL,
                   default=30,
                   min=30,
                   help='interval between checking changes in zabbix'
                        ' data source'),
    ]

    ZABBIX_OPTS_PULL_NO_INTERVAL = [
        cfg.StrOpt(DSOpts.DRIVER,
                   default='vitrage.datasources.zabbix.driver.ZabbixDriver',
                   help='Zabbix driver class path',
                   required=True),
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.PULL,
                   required=True),
    ]

    ZABBIX_OPTS_NONE = [
        cfg.StrOpt(DSOpts.DRIVER,
                   default='vitrage.datasources.zabbix.driver.ZabbixDriver',
                   help='Zabbix driver class path',
                   required=True),
        cfg.StrOpt(DSOpts.UPDATE_METHOD,
                   default=UpdateMethod.NONE,
                   required=True),
        cfg.IntOpt(DSOpts.CHANGES_INTERVAL,
                   default=30,
                   min=30,
                   help='interval between checking changes in zabbix'
                        ' data source'),
    ]

    def setUp(self):
        super(DatasourceUpdateMethod, self).setUp()
        self.conf_reregister_opts(self.DATASOURCES_OPTS, 'datasources')
        self.conf_reregister_opts(self.NOVA_HOST_OPTS, NOVA_HOST_DATASOURCE)
        self.conf_reregister_opts(self.NOVA_INSTANCE_OPTS,
                                  NOVA_INSTANCE_DATASOURCE)
        self.conf_reregister_opts(self.NAGIOS_OPTS, NAGIOS_DATASOURCE)
        self.conf_reregister_opts(self.ZABBIX_OPTS_NONE,
                                  ZABBIX_DATASOURCE_NONE)
        self.conf_reregister_opts(self.ZABBIX_OPTS_PULL,
                                  ZABBIX_DATASOURCE_PULL)
        self.conf_reregister_opts(self.ZABBIX_OPTS_PUSH,
                                  ZABBIX_DATASOURCE_PUSH)
        self.conf_reregister_opts(self.ZABBIX_OPTS_PULL_NO_INTERVAL,
                                  ZABBIX_DATASOURCE_PULL_NO_INTERVAL)

    def test_datasource_update_method_none(self):
        none_drivers = tuple(driver for driver in self.conf.datasources.types
                             if self.conf[driver].update_method
                             == UpdateMethod.NONE)
        self.assertSequenceEqual(none_drivers,
                                 (NOVA_HOST_DATASOURCE,
                                  ZABBIX_DATASOURCE_NONE))

    def test_datasource_update_method_push(self):
        driver_names = ds_utils.get_push_drivers_names()
        push_drivers = ds_utils.get_drivers_by_name(driver_names)
        self.assertSequenceEqual({utils.import_class(
            self.conf[NOVA_INSTANCE_DATASOURCE].driver), utils.import_class(
            self.conf[ZABBIX_DATASOURCE_PUSH].driver)},
            set(d.__class__ for d in push_drivers))

    def test_datasource_update_method_pull(self):
        driver_names = ds_utils.get_pull_drivers_names()
        self.assertSequenceEqual(
            set([NAGIOS_DATASOURCE, ZABBIX_DATASOURCE_PULL]),
            set(driver_names))

    def test_datasources_notification_topic(self):
        self.assertEqual('vitrage_notifications',
                         self.conf.datasources.notification_topic)
