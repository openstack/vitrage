# Copyright 2016 - Nokia
# Copyright 2015 eNovance <licensing@enovance.com>
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

import os


from keystoneauth1 import exceptions as ka_exception
from keystoneauth1 import loading as ka_loading
from keystoneauth1 import session
# noinspection PyPackageRequirements
from keystoneclient.v3 import client as ks_client_v3
from oslo_config import cfg
from oslo_log import log

CONF = cfg.CONF
LOG = log.getLogger(__name__)

CFG_GROUP = "service_credentials"


def get_session():
    """Get a vitrage service credentials auth session."""
    auth_plugin = ka_loading.load_auth_from_conf_options(CONF, CFG_GROUP)
    return ka_loading.load_session_from_conf_options(
        CONF, CFG_GROUP, auth=auth_plugin
    )


def get_client():
    """Return a client for keystone v3 endpoint."""
    sess = get_session()
    return ks_client_v3.Client(session=sess)


def get_service_catalog(client):
    return client.session.auth.get_access(client.session).service_catalog


def get_auth_token(client):
    return client.session.auth.get_access(client.session).auth_token


def get_client_on_behalf_user(auth_plugin):
    """Return a client for keystone v3 endpoint."""
    sess = session.Session(auth=auth_plugin)
    return ks_client_v3.Client(session=sess)


def create_trust_id(trustor_user_id, trustor_project_id, roles,
                    auth_plugin):
    """Create a new trust using the vitrage service user."""
    admin_client = get_client()
    trustee_user_id = admin_client.session.get_user_id()

    client = get_client_on_behalf_user(auth_plugin)
    trust = client.trusts.create(trustor_user=trustor_user_id,
                                 trustee_user=trustee_user_id,
                                 project=trustor_project_id,
                                 impersonation=True,
                                 role_names=roles)
    return trust.id


def delete_trust_id(trust_id, auth_plugin):
    """Delete a trust previously setup for the vitrage user."""
    client = get_client_on_behalf_user(auth_plugin)
    try:
        client.trusts.delete(trust_id)
    except ka_exception.NotFound:
        pass


OPTS = [
    cfg.StrOpt('region_name',
               default=os.environ.get('OS_REGION_NAME'),
               deprecated_name="region-name",
               help='Region name to use for OpenStack service endpoints.'),
    cfg.StrOpt('interface',
               default=os.environ.get(
                   'OS_INTERFACE', os.environ.get('OS_ENDPOINT_TYPE',
                                                  'public')),
               deprecated_name="os-endpoint-type",
               choices=('public', 'internal', 'admin', 'auth', 'publicURL',
                        'internalURL', 'adminURL'),
               help='Type of endpoint in Identity service catalog to use for '
                    'communication with OpenStack services.'),
]


def register_keystoneauth_opts():
    ka_loading.register_auth_conf_options(CONF, CFG_GROUP)
    ka_loading.register_session_conf_options(
        CONF, CFG_GROUP,
        deprecated_opts={'cacert': [
            cfg.DeprecatedOpt('os-cacert', group=CFG_GROUP),
            cfg.DeprecatedOpt('os-cacert', group="DEFAULT")]
        })
