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

import itertools

from vitrage.common.policies import alarms
from vitrage.common.policies import event
from vitrage.common.policies import rca
from vitrage.common.policies import resource
from vitrage.common.policies import service
from vitrage.common.policies import status
from vitrage.common.policies import template
from vitrage.common.policies import topology
from vitrage.common.policies import webhook


def list_rules():
    return itertools.chain(
        alarms.list_rules(),
        event.list_rules(),
        rca.list_rules(),
        template.list_rules(),
        topology.list_rules(),
        resource.list_rules(),
        webhook.list_rules(),
        service.list_rules(),
        status.list_rules(),
    )
