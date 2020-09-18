# Copyright 2018 - Nokia
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

import werkzeug.http

from http import client as httplib
from keystoneauth1.identity.generic import password
from keystoneauth1 import loading
from keystoneauth1 import session
from keystonemiddleware.auth_token import AuthProtocol
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from webob import exc


LOG = logging.getLogger(__name__)
CFG_GROUP = "service_credentials"


class BasicAndKeystoneAuth(AuthProtocol):

    def __init__(self, application, conf):
        super(BasicAndKeystoneAuth, self).__init__(application, conf)

        self.application = application

        self.oslo_conf = cfg.ConfigOpts()
        self.oslo_conf([],
                       project='vitrage',
                       validate_default_values=True)
        password_option = loading.get_auth_plugin_conf_options('password')
        self.oslo_conf.register_opts(password_option, group=CFG_GROUP)
        self.auth_url = self.oslo_conf.service_credentials.auth_url or ''

    @property
    def reject_auth_headers(self):
        header_val = 'Keystone uri=\'%s\'' % self.auth_url
        return [('WWW-Authenticate', header_val)]

    def process_request(self, req):
        """Process request.

            Evaluate the headers in a request and attempt to authenticate the
            request according to authentication mode.
            If the request comes through /v1/event api path then it can be
            authenticate either with basic auth by providing username and
            password or with keystone authentication.
            If authenticated then additional headers are added to the
            request for use by applications. If not authenticated the request
            will be rejected or marked unauthenticated depending on
            configuration.
        """
        if req.path == '/v1/event':
            basic_auth_info = self._get_basic_authenticator(req)
            if basic_auth_info:
                self._basic_authenticate(basic_auth_info, req)

            else:
                super(BasicAndKeystoneAuth, self).process_request(req)
        else:
            super(BasicAndKeystoneAuth, self).process_request(req)

    def _basic_authenticate(self, auth_info, req):
        try:
            project_domain_id, project_name, user_domain_id = \
                self._get_auth_params()
            auth = password.Password(auth_url=self.auth_url,
                                     username=auth_info.username,
                                     password=auth_info.password,
                                     user_domain_id=user_domain_id,
                                     project_domain_id=project_domain_id,
                                     project_name=project_name)
            sess = session.Session(auth=auth)
            token = sess.get_token()
            project_id = str(auth.get_project_id(sess))
            roles = str(auth.get_auth_ref(sess).role_names[0])
            self._set_req_headers(req, token, project_id, roles)
        except Exception as e:
            to_unicode = encodeutils.exception_to_unicode(e)
            message = 'Authorization exception: %s' % to_unicode
            self._unauthorized(message)

    def _get_auth_params(self):
        user_domain_id = \
            self.oslo_conf.service_credentials.user_domain_id
        project_domain_id = \
            self.oslo_conf.service_credentials.project_domain_id
        project_name = self.oslo_conf.service_credentials.project_name
        return project_domain_id, project_name, user_domain_id

    def _unauthorized(self, message):
        body = {'error': {
            'code': httplib.UNAUTHORIZED,
            'title': httplib.responses.get(httplib.UNAUTHORIZED),
            'message': message,
        }}

        raise exc.HTTPUnauthorized(body=jsonutils.dumps(body),
                                   headers=self.reject_auth_headers,
                                   charset='UTF-8',
                                   content_type='application/json')

    @staticmethod
    def _get_basic_authenticator(req):
        auth = werkzeug.http.parse_authorization_header(
            req.headers.get("Authorization"))
        return auth

    @staticmethod
    def _set_req_headers(req, token, project_id, roles):
        req.headers['X-Auth-Token'] = token
        req.headers['X-Identity-Status'] = 'Confirmed'
        req.headers['X-Project-Id'] = project_id
        req.headers['X-Roles'] = roles


def filter_factory(global_conf, **local_conf):
    """Return a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def auth_filter(app):
        return BasicAndKeystoneAuth(app, conf)

    return auth_filter
