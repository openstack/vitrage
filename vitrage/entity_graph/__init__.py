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

from oslo_config import cfg

from stevedore import driver

CONF = cfg.CONF

OPTS = [
    cfg.StrOpt('datasources_values_dir',
               default='/etc/vitrage/datasources_values',
               help='A path for the configuration files of the data sources'
                    ' values'
               ),
    cfg.StrOpt('notifier_topic',
               default='vitrage.graph',
               help='The topic that vitrage-graph uses for graph '
                    'notification messages.'),
    cfg.StrOpt('graph_driver',
               default='networkx',
               help='graph driver implementation class'),
]

EVALUATOR_TOPIC = 'vitrage.evaluator'


def get_graph_driver():
    try:
        mgr = driver.DriverManager('vitrage.entity_graph',
                                   CONF.entity_graph.graph_driver,
                                   invoke_on_load=True)
        return mgr.driver
    except ImportError:
        return None
