# Copyright 2015 - Alcatel-Lucent
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


# Register options for the service
OPTS = [
    cfg.PortOpt('port', default=8999,
                help='The port for the vitrage API server.',),
    cfg.StrOpt('host', default='0.0.0.0',
               help='The listen IP for the vitrage API server.',),
    cfg.StrOpt('paste_config', default='api-paste.ini',
               help='Configuration file for WSGI definition of API.'),
    cfg.IntOpt('workers', default=1, min=1,
               help='Number of workers for vitrage API server.'),
    cfg.StrOpt('auth_mode', default='keystone', choices={'keystone',
                                                         'noauth',
                                                         'keycloak'},
               help='Authentication mode to use.'),
    cfg.BoolOpt('check_backend', default=True,
                help='Check that backend is ready before an api call')
]
