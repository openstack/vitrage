# Copyright 2017 - Nokia
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
from oslo_log import log
import oslo_messaging

from vitrage.common.constants import NotifierEventTypes
from vitrage.messaging import get_transport


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class EvaluatorNotifier(object):
    """Allows writing to message bus"""
    def __init__(self, ):
        self.oslo_notifiers = {}
        try:
            notifier_plugins = CONF.notifiers

            LOG.debug('notifier_plugins: %s', notifier_plugins)

            if not notifier_plugins:
                LOG.info('Evaluator Notifier is disabled')
                return

            topic_prefix = \
                CONF.evaluator_actions.evaluator_notification_topic_prefix

            for notifier in notifier_plugins:
                LOG.debug('Adding evaluator notifier %s', notifier)

                self.oslo_notifiers[notifier] = oslo_messaging.Notifier(
                    get_transport(),
                    driver='messagingv2',
                    publisher_id='vitrage.evaluator',
                    topics=[topic_prefix + '.' + notifier])

        except Exception:
            LOG.exception('Evaluator Notifier - missing configuration')

    @property
    def enabled(self):
        return len(self.oslo_notifiers) > 0

    def notify(self, execution_engine, properties):
        """Send a message to the wanted notifier

        :param execution_engine: the external engine that should handle the
               notification and execute an action
        :param properties: Properties to be processed by the external engine
        """

        LOG.debug('execution_engine: %s, properties: %s',
                  execution_engine,
                  properties)

        try:
            if execution_engine in self.oslo_notifiers:
                LOG.debug('Notifying %s', execution_engine)
                self.oslo_notifiers[execution_engine].info(
                    {},
                    NotifierEventTypes.EXECUTE_EXTERNAL_ACTION,
                    properties)
        except Exception:
            LOG.exception('Cannot notify - %s.',
                          NotifierEventTypes.EXECUTE_EXTERNAL_ACTION)
