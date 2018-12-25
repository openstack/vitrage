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

from oslo_policy import policy

from vitrage.common.policies import base

rules = [
    policy.DocumentedRuleDefault(
        name='get resource',
        check_str=base.UNPROTECTED,
        description='Show the details of specified resource',
        operations=[
            {
                'path': '/resources',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name='list resources',
        check_str=base.UNPROTECTED,
        description='List the resources with the specified type, or all the '
                    'resources',
        operations=[
            {
                'path': '/resources',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name='list resources:all_tenants',
        check_str=base.ROLE_ADMIN,
        description='List the resources with the specified type, or all the '
                    'resources. Include resources of all tenants (if the user'
                    ' has the permissions)',
        operations=[
            {
                'path': '/resources',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name='count resources',
        check_str=base.UNPROTECTED,
        description='count the resources with the specified type, or all the '
                    'resources',
        operations=[
            {
                'path': '/resources/count',
                'method': 'GET'
            }
        ]
    ),
    policy.DocumentedRuleDefault(
        name='count resources:all_tenants',
        check_str=base.ROLE_ADMIN,
        description='Count the resources with the specified type, or all the '
                    'resources. Include resources of all tenants (if the user'
                    ' has the permissions)',
        operations=[
            {
                'path': '/resources/count',
                'method': 'GET'
            }
        ]
    )
]


def list_rules():
    return rules
