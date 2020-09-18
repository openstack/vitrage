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
import json
import jwt
import os
import requests
import urllib

from cachetools import cached
from cachetools import LRUCache
from jwt.algorithms import RSAAlgorithm
from oslo_config import cfg
from oslo_log import log as logging
from oslo_middleware import base
from oslo_serialization import jsonutils
from pecan.core import abort
from webob import exc


LOG = logging.getLogger(__name__)


KEYCLOAK_GROUP = 'keycloak'
KEYCLOAK_OPTS = [
    cfg.StrOpt('auth_url', default='http://127.0.0.1:9080/auth',
               help='Keycloak authentication server ip',),
    cfg.StrOpt('insecure', default=False,
               help='If True, SSL/TLS certificate verification is disabled'),
    cfg.StrOpt('certfile',
               help='Required if identity server requires client certificate'),
    cfg.StrOpt('keyfile',
               help='Required if identity server requires client certificate'),
    cfg.StrOpt('cafile',
               help='A PEM encoded Certificate Authority to use when verifying'
               ' HTTPs connections. Defaults to system CAs.'),
    cfg.StrOpt(
        'user_info_endpoint_url',
        default='/realms/%s/protocol/openid-connect/userinfo',
        help='Endpoint against which authorization will be performed'
    ),
    cfg.StrOpt(
        'public_cert_url',
        default="/realms/%s/protocol/openid-connect/certs",
        help="URL to get the public key for particular realm"
        ),
    cfg.StrOpt(
        'keycloak_iss',
        help="keycloak issuer(iss) url "
             "Example: https://ip_add:port/auth/realms/%s"
    )
]


class KeycloakAuth(base.ConfigurableMiddleware):

    def __init__(self, application, conf=None):
        super(KeycloakAuth, self).__init__(application, conf)

        self.oslo_conf.register_opts(KEYCLOAK_OPTS, '%s' % KEYCLOAK_GROUP)
        self.auth_url = self._conf_get('auth_url', KEYCLOAK_GROUP)
        self.insecure = self._conf_get('insecure', KEYCLOAK_GROUP)
        self.certfile = self._conf_get('certfile', KEYCLOAK_GROUP)
        self.keyfile = self._conf_get('keyfile', KEYCLOAK_GROUP)
        self.cafile = self._conf_get('cafile', KEYCLOAK_GROUP) or \
            self._get_system_ca_file()
        self.user_info_endpoint_url = self._conf_get('user_info_endpoint_url',
                                                     KEYCLOAK_GROUP)
        self.public_cert_url = self._conf_get('public_cert_url',
                                              KEYCLOAK_GROUP)
        self.keycloak_iss = self._conf_get('keycloak_iss', KEYCLOAK_GROUP)

    @property
    def reject_auth_headers(self):
        header_val = 'Keycloak uri=\'%s\'' % self.auth_url
        return [('WWW-Authenticate', header_val)]

    @staticmethod
    def roles(decoded):
        return ','.join(decoded['realm_access']['roles']) \
            if 'realm_access' in decoded else ''

    @staticmethod
    def realm_name(decoded):
        # Get user realm from parsed token
        # Format is "iss": "http://<host>:<port>/auth/realms/<realm_name>",
        __, __, realm_name = decoded['iss'].strip().rpartition('/realms/')
        return realm_name

    def process_request(self, req):
        self._authenticate(req)

    def _authenticate(self, req):
        decoded = {}
        token = req.headers.get('X-Auth-Token')
        if token:
            decoded = self._decode(token)
        else:
            message = 'Auth token must be provided in "X-Auth-Token" header.'
            self._unauthorized(message)

        self.call_keycloak(token, decoded, decoded.get('aud'))

        self._set_req_headers(req, decoded)

    def _decode(self, token):
        try:
            return jwt.decode(token, algorithms=['RS256'], verify=False)
        except jwt.DecodeError:
            message = "Token can't be decoded because of wrong format."
            self._unauthorized(message)

    def call_keycloak(self, token, decoded, audience):
        if self.user_info_endpoint_url.startswith(('http://', 'https://')):
            endpoint = self.user_info_endpoint_url
            self.send_request_to_auth_server(endpoint, token)
        else:
            public_key = self.get_public_key(self.realm_name(decoded))
            try:
                if self.keycloak_iss:
                    self.keycloak_iss = self.keycloak_iss % \
                        self.realm_name(decoded)
                jwt.decode(token, public_key, audience=audience,
                           issuer=self.keycloak_iss, algorithms=['RS256'],
                           verify=True)
            except Exception:
                message = 'Token validation failure'
                self._unauthorized(message)

    def send_request_to_auth_server(self, endpoint, token=None):
        headers = {}
        if token:
            headers = {'Authorization': 'Bearer %s' % token}
        verify = None
        if urllib.parse.urlparse(endpoint).scheme == "https":
            verify = False if self.insecure else self.cafile
        cert = (self.certfile, self.keyfile) \
            if self.certfile and self.keyfile else None
        resp = requests.get(endpoint, headers=headers,
                            verify=verify, cert=cert)
        if not resp.ok:
            abort(resp.status_code, resp.reason)
        return resp.json()

    def _set_req_headers(self, req, decoded):
        req.headers['X-Identity-Status'] = 'Confirmed'
        req.headers['X-Roles'] = self.roles(decoded)
        req.headers["X-Project-Id"] = self.realm_name(decoded)

    def _unauthorized(self, message):
        body = {'error': {
            'code': 401,
            'title': 'Unauthorized',
            'message': message,
        }}

        raise exc.HTTPUnauthorized(body=jsonutils.dumps(body),
                                   headers=self.reject_auth_headers,
                                   charset='UTF-8',
                                   content_type='application/json')

    @staticmethod
    def _get_system_ca_file():
        """Return path to system default CA file."""
        # Standard CA file locations for Debian/Ubuntu, RedHat/Fedora,
        # Suse, FreeBSD/OpenBSD, MacOSX, and the bundled ca
        ca_path = ['/etc/ssl/certs/ca-certificates.crt',
                   '/etc/pki/tls/certs/ca-bundle.crt',
                   '/etc/ssl/ca-bundle.pem',
                   '/etc/ssl/cert.pem',
                   '/System/Library/OpenSSL/certs/cacert.pem',
                   requests.certs.where()]
        for ca in ca_path:
            LOG.debug("Looking for ca file %s", ca)
            if os.path.exists(ca):
                LOG.debug("Using ca file %s", ca)
                return ca
        LOG.warning("System ca file could not be found.")

    @cached(LRUCache(maxsize=32))
    def get_public_key(self, realm_name):
        keycloak_key_url = self.auth_url + self.public_cert_url % realm_name
        response_json = self.send_request_to_auth_server(keycloak_key_url)
        public_key = RSAAlgorithm.from_jwk(
            json.dumps(response_json["keys"][0]))
        return public_key


filter_factory = KeycloakAuth.factory
