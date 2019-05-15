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
from oslo_db import options as db_options
from oslo_log import log
from oslo_policy import opts as policy_opts
from osprofiler import initializer as osprofiler_initializer
from osprofiler import opts as osprofiler_opts
from vitrage import keystone_client
from vitrage import messaging
from vitrage import opts


CONF = cfg.CONF
LOG = log.getLogger(__name__)


def parse_config(args, default_config_files=None):
    set_defaults()
    log.register_options(CONF)
    policy_opts.set_defaults(CONF)
    osprofiler_opts.set_defaults(CONF)
    db_options.set_defaults(CONF)

    for group, options in opts.list_opts():
        CONF.register_opts(list(options),
                           group=None if group == 'DEFAULT' else group)

    CONF(args[1:], project='vitrage', validate_default_values=True,
         default_config_files=default_config_files)

    if CONF.profiler.enabled:
        osprofiler_initializer.init_from_conf(
            conf=CONF,
            context=None,
            project='vitrage',
            service='api',
            host=CONF.api.host
        )

    for datasource in CONF.datasources.types:
        opts.register_opts(datasource, CONF.datasources.path)

    keystone_client.register_keystoneauth_opts()
    log.setup(CONF, 'vitrage')
    CONF.log_opt_values(LOG, log.DEBUG)
    messaging.setup()


def set_defaults():
    from oslo_middleware import cors
    cfg.set_defaults(cors.CORS_OPTS,
                     allow_headers=[
                         'Authorization',
                         'X-Auth-Token',
                         'X-Subject-Token',
                         'X-User-Id',
                         'X-Domain-Id',
                         'X-Project-Id',
                         'X-Roles'])
