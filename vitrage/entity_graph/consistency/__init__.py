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


OPTS = [
    cfg.IntOpt('min_time_to_delete',
               default=60,
               min=60,
               help='minimum time until deleting entity (in seconds)'),
    cfg.IntOpt('initialization_interval',
               default=1,
               min=1,
               deprecated_for_removal=True,
               deprecated_since='Stein',
               deprecated_reason='This config option is no longer used.',
               help='interval between consistency initialization checks for '
                    'finding if all end messages from datasources were '
                    'received (in seconds)'),
    cfg.IntOpt('initialization_max_retries',
               default=30,
               min=1,
               deprecated_for_removal=True,
               deprecated_since='Stein',
               deprecated_reason='This config option is no longer used.',
               help='maximum retries for consistency initialization '
                    'for finding if all end messages from datasources were '
                    'received (in seconds)'),
]
