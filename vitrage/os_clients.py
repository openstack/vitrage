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

LOG = log.getLogger(__name__)

OPTS = [
    cfg.StrOpt('aodh_version', default='2', help='Aodh version'),
    cfg.StrOpt('ceilometer_version', default='2', help='Ceilometer version'),
    cfg.StrOpt('nova_version', default='2.11', help='Nova version'),
    cfg.StrOpt('cinder_version', default='2', help='Cinder version'),
    cfg.StrOpt('glance_version', default='2', help='Glance version'),
    cfg.StrOpt('heat_version', default='1', help='Heat version'),
    cfg.StrOpt('mistral_version', default='2', help='Mistral version'),
    cfg.StrOpt('gnocchi_version', default='1', help='Gnocchi version'),
    cfg.StrOpt('trove_version', default='1', help='Trove version'),
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
    'ceilometer': 'ceilometerclient.client',
    'nova': 'novaclient.client',
    'cinder': 'cinderclient.client',
    'glance': 'glanceclient.client',
    'neutron': 'neutronclient.v2_0.client',
    'heat': 'heatclient.client',
    'mistral': 'mistralclient.api.v2.client',
    'gnocchi': 'gnocchiclient.v1.client',
    'trove': 'troveclient.v1.client'
}


def driver_module(driver):
    mod_name = _client_modules[driver]
    module = utils.import_module(mod_name)
    return module


def gnocchi_client(conf):
    """Get an instance of the gnocchi client"""
    try:
        gn_client = driver_module('gnocchi')
        client = gn_client.Client(
            session=keystone_client.get_session(conf))
        LOG.info('Gnocchi client created')
        return client
    except Exception:
        LOG.exception('Create Gnocchi client - Got Exception')


def aodh_client(conf):
    """Get an instance of aodh client"""
    try:
        ao_client = driver_module('aodh')
        client = ao_client.Client(
            conf.aodh_version,
            session=keystone_client.get_session(conf))
        LOG.info('Aodh client created')
        return client
    except Exception:
        LOG.exception('Create Aodh client - Got Exception.')


def ceilometer_client(conf):
    """Get an instance of ceilometer client"""
    try:
        cm_client = driver_module('ceilometer')
        client = cm_client.get_client(
            version=conf.ceilometer_version,
            session=keystone_client.get_session(conf),
        )
        LOG.info('Ceilometer client created')
        return client
    except Exception:
        LOG.exception('Create Ceilometer client - Got Exception.')


def nova_client(conf):
    """Get an instance of nova client"""
    try:
        n_client = driver_module('nova')
        client = n_client.Client(
            version=conf.nova_version,
            session=keystone_client.get_session(conf),
        )
        LOG.info('Nova client created')
        return client
    except Exception:
        LOG.exception('Create Nova client - Got Exception.')


def trove_client(conf):
    """Get an instance of trove client"""
    try:
        tr_client = driver_module('trove')
        client = tr_client.Client(
            version=conf.trove_version,
            session=keystone_client.get_session(conf),
        )
        LOG.info('Trove client created')
        return client
    except Exception:
        LOG.exception('Create Trove client - Got Exception.')


def cinder_client(conf):
    """Get an instance of cinder client"""
    try:
        cin_client = driver_module('cinder')
        client = cin_client.Client(
            version=conf.cinder_version,
            session=keystone_client.get_session(conf),
        )
        LOG.info('Cinder client created')
        return client
    except Exception:
        LOG.exception('Create Cinder client - Got Exception.')


def glance_client(conf):
    """Get an instance of glance client"""
    try:
        glan_client = driver_module('glance')
        client = glan_client.Client(
            version=conf.glance_version,
            session=keystone_client.get_session(conf),
        )
        LOG.info('Glance client created')
        return client
    except Exception:
        LOG.exception('Create Glance client - Got Exception')


def neutron_client(conf):
    """Get an instance of neutron client"""
    try:
        ne_client = driver_module('neutron')
        client = ne_client.Client(
            session=keystone_client.get_session(conf)
        )
        LOG.info('Neutron client created')
        return client
    except Exception:
        LOG.exception('Create Neutron client - Got Exception.')


def heat_client(conf):
    """Get an instance of heat client"""
    try:
        he_client = driver_module('heat')
        client = he_client.Client(
            version=conf.heat_version,
            session=keystone_client.get_session(conf)
        )
        LOG.info('Heat client created')
        return client
    except Exception:
        LOG.exception('Create Heat client - Got Exception.')


def mistral_client(conf):
    """Get an instance of Mistral client"""
    try:
        mi_client = driver_module('mistral')
        client = mi_client.Client(
            session=keystone_client.get_session(conf),
        )
        LOG.info('Mistral client created')
        return client
    except Exception:
        LOG.exception('Create Mistral client - Got Exception.')


def zaqar_client(conf):
    """Get an instance of Zaqar client"""
    try:
        z_client = driver_module('zaqar')
        client = z_client.Client(
            session=keystone_client.get_session(conf),
        )
        LOG.info('Zaqar client created')
        return client
    except Exception:
        LOG.exception('Create Zaqar client - Got Exception.')
