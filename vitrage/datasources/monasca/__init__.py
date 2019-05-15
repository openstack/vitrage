# Copyright 2018 Samsung Electronics
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg
from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import UpdateMethod

MONASCA_DATASOURCE = 'monasca'

OPTS = [
    cfg.StrOpt(DSOpts.TRANSFORMER,
               default='vitrage.datasources.monasca.transformer.'
                       'MonascaTransformer',
               help='Monasca transformer class path.',
               required=True),
    cfg.StrOpt(DSOpts.DRIVER,
               default='vitrage.datasources.monasca.driver.'
                       'MonascaDriver',
               help='Monasca driver class path.',
               required=True),
    cfg.StrOpt(DSOpts.UPDATE_METHOD,
               default=UpdateMethod.PULL,
               help='None: updates only via Vitrage periodic snapshots.'
                    'Pull: updates periodically.'
                    'Push: updates by getting notifications from the'
                    ' datasource itself.',
               required=True),
    cfg.IntOpt(DSOpts.CHANGES_INTERVAL,
               default=30,
               min=10,
               help='Interval in seconds between checking changes in Monasca'
                    'datasource.'),
    ]
