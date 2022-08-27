# Copyright 2016 - Nokia
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
from oslo_utils import importutils as utils

from vitrage import keystone_client

CONF = cfg.CONF
LOG = log.getLogger(__name__)

OPTS = [
    cfg.StrOpt('aodh_version', default='2', help='Aodh version'),
    cfg.StrOpt('nova_version', default='2.11', help='Nova version'),
    cfg.StrOpt('cinder_version', default='3', help='Cinder version'),
    cfg.StrOpt('glance_version', default='2', help='Glance version'),
    cfg.StrOpt('heat_version', default='1', help='Heat version'),
    cfg.StrOpt('mistral_version', default='2', help='Mistral version'),
    cfg.StrOpt('gnocchi_version', default='1', help='Gnocchi version'),
    cfg.StrOpt('trove_version', default='1', help='Trove version'),
    cfg.StrOpt('monasca_version', default='2_0', help='Monasca version'),
    cfg.BoolOpt('use_nova_versioned_notifications',
                default=True,
                help='Indicates whether to use Nova versioned notifications.'
                     'The default is True. If False, the deprecated Nova '
                     'legacy notifications will be used.'
                     'This flag must be set to False if notification_format '
                     'is set to "unversioned" in nova.conf'),
]

_client_modules = {
    'aodh': 'aodhclient.client',
    'nova': 'novaclient.client',
    'cinder': 'cinderclient.client',
    'glance': 'glanceclient.client',
    'neutron': 'neutronclient.v2_0.client',
    'heat': 'heatclient.client',
    'mistral': 'mistralclient.api.v2.client',
    'gnocchi': 'gnocchiclient.v1.client',
    'trove': 'troveclient.v1.client',
    'monasca': 'monascaclient.client'
}


def driver_module(driver):
    mod_name = _client_modules[driver]
    module = utils.import_module(mod_name)
    return module


def gnocchi_client():
    """Get an instance of the gnocchi client"""
    try:
        gn_client = driver_module('gnocchi')
        client = gn_client.Client(
            session=keystone_client.get_session())
        LOG.info('Gnocchi client created')
        return client
    except Exception:
        LOG.exception('Create Gnocchi client - Got Exception')


def aodh_client():
    """Get an instance of aodh client"""
    try:
        ao_client = driver_module('aodh')
        client = ao_client.Client(
            CONF.aodh_version,
            session=keystone_client.get_session())
        LOG.info('Aodh client created')
        return client
    except Exception:
        LOG.exception('Create Aodh client - Got Exception.')


def nova_client():
    """Get an instance of nova client"""
    try:
        n_client = driver_module('nova')
        client = n_client.Client(
            version=CONF.nova_version,
            region_name=CONF.service_credentials.region_name,
            session=keystone_client.get_session(),
        )
        LOG.info('Nova client created')
        return client
    except Exception:
        LOG.exception('Create Nova client - Got Exception.')


def trove_client():
    """Get an instance of trove client"""
    try:
        tr_client = driver_module('trove')
        client = tr_client.Client(
            version=CONF.trove_version,
            region_name=CONF.service_credentials.region_name,
            session=keystone_client.get_session(),
        )
        LOG.info('Trove client created')
        return client
    except Exception:
        LOG.exception('Create Trove client - Got Exception.')


def cinder_client():
    """Get an instance of cinder client"""
    try:
        cin_client = driver_module('cinder')
        client = cin_client.Client(
            version=CONF.cinder_version,
            region_name=CONF.service_credentials.region_name,
            session=keystone_client.get_session(),
        )
        LOG.info('Cinder client created')
        return client
    except Exception:
        LOG.exception('Create Cinder client - Got Exception.')


def glance_client():
    """Get an instance of glance client"""
    try:
        glan_client = driver_module('glance')
        client = glan_client.Client(
            version=CONF.glance_version,
            session=keystone_client.get_session(),
        )
        LOG.info('Glance client created')
        return client
    except Exception:
        LOG.exception('Create Glance client - Got Exception')


def neutron_client():
    """Get an instance of neutron client"""
    try:
        ne_client = driver_module('neutron')
        client = ne_client.Client(
            region_name=CONF.service_credentials.region_name,
            session=keystone_client.get_session()
        )
        LOG.info('Neutron client created')
        return client
    except Exception:
        LOG.exception('Create Neutron client - Got Exception.')


def heat_client():
    """Get an instance of heat client"""
    try:
        he_client = driver_module('heat')
        client = he_client.Client(
            version=CONF.heat_version,
            region_name=CONF.service_credentials.region_name,
            session=keystone_client.get_session()
        )
        LOG.info('Heat client created')
        return client
    except Exception:
        LOG.exception('Create Heat client - Got Exception.')


def mistral_client():
    """Get an instance of Mistral client"""
    try:
        mi_client = driver_module('mistral')
        client = mi_client.Client(
            region_name=CONF.service_credentials.region_name,
            session=keystone_client.get_session(),
        )
        LOG.info('Mistral client created')
        return client
    except Exception:
        LOG.exception('Create Mistral client - Got Exception.')


def zaqar_client():
    """Get an instance of Zaqar client"""
    try:
        z_client = driver_module('zaqar')
        client = z_client.Client(
            session=keystone_client.get_session(),
        )
        LOG.info('Zaqar client created')
        return client
    except Exception:
        LOG.exception('Create Zaqar client - Got Exception.')


def monasca_client():
    """Get an instance of Monasca client"""
    try:
        mon_client = driver_module('monasca')

        session = keystone_client.get_session()
        endpoint = session.get_endpoint(service_type='monitoring',
                                        interface='publicURL')
        client = mon_client.Client(
            api_version=CONF.monasca_version,
            session=session,
            endpoint=endpoint
        )
        LOG.info('Monasca client created')
        return client
    except Exception:
        LOG.exception('Create Monasca client - Got Exception.')
