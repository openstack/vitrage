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
from stevedore import driver
import tenacity
from urllib import parse as urlparse

from vitrage.utils.datetime import utcnow

_NAMESPACE = 'vitrage.storage'

CONF = cfg.CONF
LOG = log.getLogger(__name__)


OPTS = []


def get_connection_from_config():
    retries = CONF.database.max_retries
    url = CONF.database.connection

    try:
        # TOTO(iafek): check why this call randomly fails
        connection_scheme = urlparse.urlparse(url).scheme
        LOG.debug('looking for %(name)r driver in %(namespace)r',
                  {'name': connection_scheme, 'namespace': _NAMESPACE})
        mgr = driver.DriverManager(_NAMESPACE, connection_scheme)

    except Exception:
        LOG.exception('Failed to get scheme %s.' % url)
        return None

    @tenacity.retry(
        wait=tenacity.wait_fixed(CONF.database.retry_interval),
        stop=tenacity.stop_after_attempt(retries),
        after=tenacity.after_log(LOG, log.WARN),
        reraise=True)
    def _get_connection():
        """Return an open connection to the database."""
        conn = mgr.driver(url)
        session = conn._engine_facade.get_session()
        session.execute('SELECT 1;')
        return conn

    return _get_connection()


def db_time():
    ret = utcnow(with_timezone=False)
    return ret.replace(microsecond=0)
