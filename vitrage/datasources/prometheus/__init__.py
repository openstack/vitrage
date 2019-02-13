# Copyright 2018 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,  software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND,  either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import UpdateMethod
from vitrage.datasources.prometheus.properties \
    import PrometheusGetAllProperties as PGAProps

PROMETHEUS_DATASOURCE = 'prometheus'

OPTS = [
    cfg.StrOpt(DSOpts.TRANSFORMER,
               default='vitrage.datasources.prometheus.transformer.'
                       'PrometheusTransformer',
               help='Prometheus transformer class path',
               required=True),
    cfg.StrOpt(DSOpts.DRIVER,
               default='vitrage.datasources.prometheus.driver.'
                       'PrometheusDriver',
               help='Prometheus driver class path',
               required=True),
    cfg.StrOpt(DSOpts.UPDATE_METHOD,
               default=UpdateMethod.PUSH,
               help='None: updates only via Vitrage periodic snapshots.'
                    'Pull: updates every [changes_interval] seconds.'
                    'Push: updates by getting notifications from the'
                    ' datasource itself.',
               required=True),
    cfg.StrOpt(DSOpts.CONFIG_FILE, default='/etc/vitrage/prometheus_conf.yaml',
               help='Prometheus configuration file'),
    cfg.StrOpt(PGAProps.ALERTMANAGER_URL,
               help='Prometheus Alertmanager http api url to get alerts'),
    cfg.StrOpt(PGAProps.RECEIVER,
               help='Receiver configured in Prometheus Alertmanager to send '
                    'alerts to Vitrage'),
]
