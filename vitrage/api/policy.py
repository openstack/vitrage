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

from pecan.core import abort

from vitrage.utils import recursive_keypairs


def enforce(rule, headers, enforcer, target):
    """Return the user and project the request should be limited to.

    :param headers: the request headers
    :param rule: The rule name
    :param enforcer: policy enforcer
    :param target: The target to enforce on.

    """
    creds = {
        'roles': headers.get('X-Roles', '').split(','),
        'user_id': headers.get('X-User-Id'),
        'project_id': headers.get('X-Project-Id'),
    }

    if not isinstance(target, dict):
        target = vars(target)

    target = dict(recursive_keypairs(target))

    if not enforcer.enforce(rule, target, creds):
        abort(status_code=403,
              detail='Authorization Failed')
