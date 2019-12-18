# Copyright 2017 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from oslo_log import log
import oslo_messaging as oslo_m
from oslo_utils import importutils

from vitrage.coordination import service as coord
from vitrage import messaging
from vitrage.opts import register_opts

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class MachineLearningService(coord.Service):

    def __init__(self, worker_id):
        super(MachineLearningService, self).__init__(worker_id)
        self.machine_learning_plugins = self.get_machine_learning_plugins()
        transport = messaging.get_transport()
        target = \
            oslo_m.Target(topic=CONF.machine_learning.machine_learning_topic)
        self.listener = messaging.get_notification_listener(
            transport, [target],
            [VitrageEventEndpoint(self.machine_learning_plugins)])

    def run(self):
        super(MachineLearningService, self).run()
        LOG.info("Vitrage Machine Learning Service - Starting...")

        self.listener.start()

        LOG.info("Vitrage Machine Learning Service - Started!")

    def terminate(self):
        super(MachineLearningService, self).terminate()
        LOG.info("Vitrage Machine Learning Service - Stopping...")

        self.listener.stop()
        self.listener.wait()

        LOG.info("Vitrage Machine Learning Service - Stopped!")

    @staticmethod
    def get_machine_learning_plugins():
        machine_learning_plugins = []
        machine_learning_plugins_names = \
            CONF.machine_learning.plugins
        if not machine_learning_plugins_names:
            LOG.info('There are no Machine Learning plugins in configuration')
            return []
        for machine_learning_plugin_name in machine_learning_plugins_names:
            register_opts(machine_learning_plugin_name,
                          CONF.machine_learning.plugins_path)
            LOG.info('Machine Learning plugin %s started',
                     machine_learning_plugin_name)
            machine_learning_plugins.append(importutils.import_object(
                CONF[machine_learning_plugin_name].plugin_path))
        return machine_learning_plugins


class VitrageEventEndpoint(object):

    def __init__(self, machine_learning_plugins):
        self.machine_learning_plugins = machine_learning_plugins

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        """Endpoint for alarm notifications"""
        LOG.info('Vitrage Event Info: event_type %s', event_type)
        LOG.info('Vitrage Event Info: payload %s', payload)
        for plugin in self.machine_learning_plugins:
            plugin.process_event(payload, event_type)
