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

import os

import pecan

from oslo_config import cfg
from oslo_log import log
from oslo_utils import uuidutils
# noinspection PyPackageRequirements
from paste import deploy
from werkzeug import serving

from vitrage.api import hooks

LOG = log.getLogger(__name__)

# NOTE(sileht): pastedeploy uses ConfigParser to handle
# global_conf, since python 3 ConfigParser doesn't
# allow storing object as config value, only strings are
# permit, so to be able to pass an object created before paste load
# the app, we store them into a global var. But the each loaded app
# store it's configuration in unique key to be concurrency safe.
global APPCONFIGS
APPCONFIGS = {}


def setup_app(root, conf=None):
    app_hooks = [hooks.ConfigHook(conf),
                 hooks.TranslationHook(),
                 hooks.GCHook(),
                 hooks.RPCHook(conf),
                 hooks.ContextHook(),
                 hooks.DBHook(conf),
                 hooks.CoordinatorHook(conf)]

    app = pecan.make_app(
        root,
        hooks=app_hooks,
        guess_content_type_from_ext=False
    )

    return app


def load_app(conf):
    global APPCONFIGS

    # Build the WSGI app
    cfg_path = conf.api.paste_config
    if not os.path.isabs(cfg_path):
        cfg_path = conf.find_file(cfg_path)

    if cfg_path is None or not os.path.exists(cfg_path):
        raise cfg.ConfigFilesNotFoundError([conf.api.paste_config])

    config = dict(conf=conf)
    configkey = uuidutils.generate_uuid()
    APPCONFIGS[configkey] = config

    LOG.info('Full WSGI config used: %s', cfg_path)

    appname = "vitrage+" + conf.api.auth_mode
    return deploy.loadapp("config:" + cfg_path, name=appname,
                          global_conf={'configkey': configkey})


def build_server(conf):
    app = load_app(conf)
    # Create the WSGI server and start it
    host, port = conf.api.host, conf.api.port

    LOG.info('Starting server in PID %s', os.getpid())
    LOG.info('Configuration:')
    conf.log_opt_values(LOG, log.INFO)

    if host == '0.0.0.0':
        LOG.info(
            'serving on 0.0.0.0:%(port)s, view at http://127.0.0.1:%(port)s',
            {'port': port})
    else:
        LOG.info('serving on http://%(host)s:%(port)s',
                 {'host': host, 'port': port})

    serving.run_simple(host, port,
                       app, processes=conf.api.workers)


def app_factory(global_config, **local_conf):
    global APPCONFIGS
    appconfig = APPCONFIGS.get(global_config.get('configkey'))
    return setup_app(root=local_conf.get('root'), **appconfig)
