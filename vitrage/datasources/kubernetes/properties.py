# Copyright 2018 - Nokia
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


KUBERNETES_DATASOURCE = 'kubernetes'


class KubernetesProperties(object):
    NAME = 'name'
    METADATA = 'metadata'
    NETWORK = 'network'
    ADDRESS = 'address'
    STATUS = 'status'
    ADDRESSES = 'addresses'
    TYPE = 'type'
    INTERNALIP = 'internal_ip'
    EXTERNALIP = 'external_ip'
    UID = 'uid'
    EXTERNALID = 'external_id'
    PROVIDERID = 'provider_id'
    PROVIDER_NAME = 'provider_name'
    SPEC = 'spec'
    CREATION_TIMESTAMP = 'creation_timestamp'
    RESOURCES = 'resources'
