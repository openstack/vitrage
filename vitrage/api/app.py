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

import math
import os
from os import path
import sys

import pecan

from distutils import spawn
from oslo_config import cfg
from oslo_log import log
from oslo_utils import uuidutils
# noinspection PyPackageRequirements
from paste import deploy
from werkzeug import serving

from vitrage.api import hooks

CONF = cfg.CONF

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
    app_hooks = [hooks.ConfigHook(),
                 hooks.TranslationHook(),
                 hooks.GCHook(),
                 hooks.RPCHook(),
                 hooks.ContextHook(),
                 hooks.DBHook(),
                 hooks.CoordinatorHook()]

    app = pecan.make_app(
        root,
        hooks=app_hooks,
        guess_content_type_from_ext=False
    )

    return app


def load_app():
    global APPCONFIGS
    # Build the WSGI app
    cfg_path = CONF.api.paste_config
    if not os.path.isabs(cfg_path):
        cfg_path = CONF.find_file(cfg_path)

    if cfg_path is None or not os.path.exists(cfg_path):
        raise cfg.ConfigFilesNotFoundError([CONF.api.paste_config])

    config = dict(conf=CONF)
    configkey = uuidutils.generate_uuid()
    APPCONFIGS[configkey] = config

    LOG.info('Full WSGI config used: %s', cfg_path)

    appname = "vitrage+" + CONF.api.auth_mode
    return deploy.loadapp("config:" + cfg_path, name=appname,
                          global_conf={'configkey': configkey})


def build_server():
    uwsgi = spawn.find_executable("uwsgi")
    if not uwsgi:
        LOG.warning('uwsgi not installed, starting a TEST server')
        build_simple_server()
    else:
        build_uwsgi_server(uwsgi)


def wsgi_file():
    return path.join(path.dirname(__file__), 'app.wsgi')


def build_uwsgi_server(uwsgi):

    major = str(sys.version_info.major)
    minor = str(sys.version_info.minor)
    plugin = ''.join(('python', major, minor))
    args = [
        "--if-not-plugin", "python", "--plugin", plugin, "--endif",
        "--http-socket", "%s:%d" % (CONF.api.host, CONF.api.port),
        "--master",
        "--enable-threads",
        "--thunder-lock",
        "--hook-master-start", "unix_signal:15 gracefully_kill_them_all",
        "--die-on-term",
        "--processes", str(math.floor(CONF.api.workers * 1.5)),
        "--threads", str(CONF.api.workers),
        "--lazy-apps",
        "--chdir", "/",
        "--buffer-size", "65535",
        "--wsgi-file", wsgi_file(),
        "--procname-prefix", "vitrage",
        "--pyargv", " ".join(sys.argv[1:]),
    ]

    virtual_env = os.getenv("VIRTUAL_ENV")
    if virtual_env is not None:
        args.extend(["-H", os.getenv("VIRTUAL_ENV", ".")])

    return os.execl(uwsgi, uwsgi, *args)


def build_simple_server():
    app = load_app()
    # Create the WSGI server and start it
    host, port = CONF.api.host, CONF.api.port

    LOG.info('Starting server in PID %s', os.getpid())
    LOG.info('Configuration:')
    CONF.log_opt_values(LOG, log.INFO)

    if host == '0.0.0.0':
        LOG.info(
            'serving on 0.0.0.0:%(port)s, view at http://127.0.0.1:%(port)s',
            {'port': port})
    else:
        LOG.info('serving on http://%(host)s:%(port)s',
                 {'host': host, 'port': port})

    LOG.info('"DANGER! For testing only, do not use in production"')

    serving.run_simple(host, port,
                       app, processes=CONF.api.workers)


def app_factory(global_config, **local_conf):
    global APPCONFIGS
    appconfig = APPCONFIGS.get(global_config.get('configkey'))
    return setup_app(root=local_conf.get('root'), **appconfig)
