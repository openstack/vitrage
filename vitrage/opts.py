# Copyright 2015 - Alcatel-Lucent
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

import itertools
import os

from oslo_config import cfg
from oslo_log import log
from oslo_utils import importutils

import vitrage.api
import vitrage.coordination
import vitrage.datasources
import vitrage.entity_graph.consistency
import vitrage.evaluator
import vitrage.evaluator.actions
import vitrage.keystone_client
import vitrage.machine_learning
import vitrage.machine_learning.plugins.jaccard_correlation
import vitrage.notifier
import vitrage.notifier.plugins.snmp
import vitrage.notifier.plugins.webhook
import vitrage.notifier.plugins.zaqar
import vitrage.os_clients
import vitrage.persistency
import vitrage.rpc
import vitrage.snmp_parsing
import vitrage.storage

CONF = cfg.CONF
LOG = log.getLogger(__name__)

DATASOURCES_PATH = 'vitrage.datasources.'
DATASOURCE_FS_PATH = os.path.join('vitrage', 'datasources')
DRIVER_FILE = 'driver.py'
TRANSFORMER_FILE = 'alarm_transformer_base.py'


def list_opts():
    return [
        ('api', vitrage.api.OPTS),
        ('datasources', vitrage.datasources.OPTS),
        ('evaluator', vitrage.evaluator.OPTS),
        ('evaluator_actions', vitrage.evaluator.actions.OPTS),
        ('consistency', vitrage.entity_graph.consistency.OPTS),
        ('database', vitrage.storage.OPTS),
        ('persistency', vitrage.persistency.OPTS),
        ('entity_graph', vitrage.entity_graph.OPTS),
        ('service_credentials', vitrage.keystone_client.OPTS),
        ('machine_learning',
         vitrage.machine_learning.OPTS),
        ('jaccard_correlation',
         vitrage.machine_learning.plugins.jaccard_correlation.OPTS),
        ('snmp', vitrage.notifier.plugins.snmp.OPTS),
        ('webhook', vitrage.notifier.plugins.webhook.OPTS),
        ('snmp_parsing', vitrage.snmp_parsing.OPTS),
        ('zaqar', vitrage.notifier.plugins.zaqar.OPTS),
        ('coordination', vitrage.coordination.OPTS),
        ('DEFAULT', itertools.chain(
            vitrage.os_clients.OPTS,
            vitrage.rpc.OPTS,
            vitrage.notifier.OPTS))
    ]


def datasources_opts():

    top = os.getcwd()

    datasources = _normalize_path_to_datasource_name(
        _filter_folders_containing_transformer(_get_datasources_folders(top)),
        top)

    return [(datasource, module.OPTS) for datasource in datasources
            for module in
            [importutils.import_module(DATASOURCES_PATH + datasource)]
            if 'OPTS' in vars(module)]


def _get_datasources_folders(top=os.getcwd()):
    return [os.path.dirname(os.path.join(root, name))
            for root, dirs, files in os.walk(top, topdown=False)
            for name in files if name == DRIVER_FILE]


def _filter_folders_containing_transformer(folders):
    return [folder for folder in folders for
            root, dirs, files in os.walk(folder, topdown=False) for
            name in files if name == TRANSFORMER_FILE]


def _normalize_path_to_datasource_name(path_list, top=os.getcwd()):
    return [os.path.relpath(path, os.path.join(top, DATASOURCE_FS_PATH))
            .replace(os.sep, '.') for path in path_list]


def register_opts(package_name, paths):
    """register opts of package package_name, with base path in paths"""
    for path in paths:
        try:
            opt = importutils.import_module(
                "%s.%s" % (path, package_name)).OPTS
            CONF.register_opts(
                list(opt),
                group=None if package_name == 'DEFAULT' else package_name
            )
            return
        except ImportError:
            pass
    LOG.error("Failed to import config options for %s. Not found in %s",
              package_name, paths)
