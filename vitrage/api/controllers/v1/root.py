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
import gc

from vitrage.api.controllers.v1 import alarm
from vitrage.api.controllers.v1 import event
from vitrage.api.controllers.v1 import rca
from vitrage.api.controllers.v1 import resource
from vitrage.api.controllers.v1 import service
from vitrage.api.controllers.v1 import status
from vitrage.api.controllers.v1 import template
from vitrage.api.controllers.v1 import topology
from vitrage.api.controllers.v1 import webhook


class V1Controller(object):

    gc.set_threshold(1, 1, 1)

    topology = topology.TopologyController()
    resources = resource.ResourcesController()
    alarm = alarm.AlarmsController()
    rca = rca.RCAController()
    webhook = webhook.WebhookController()
    template = template.TemplateController()
    event = event.EventController()
    service = service.ServiceController()
    status = status.StatusController()
