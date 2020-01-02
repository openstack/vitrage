# Copyright 2016 - Nokia
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

from oslo_config import cfg

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import GraphAction
from vitrage.datasources.cinder.volume import CINDER_VOLUME_DATASOURCE
from vitrage.datasources.cinder.volume.driver import CinderVolumeDriver
from vitrage.datasources.driver_base import DriverBase
from vitrage.datasources.heat.stack import HEAT_STACK_DATASOURCE
from vitrage.datasources.neutron.network.driver import NetworkDriver
from vitrage.datasources.neutron.network import NEUTRON_NETWORK_DATASOURCE
from vitrage.datasources.neutron.port.driver import PortDriver
from vitrage.datasources.neutron.port import NEUTRON_PORT_DATASOURCE
from vitrage.datasources.nova.instance.driver import InstanceDriver
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage import os_clients

CONF = cfg.CONF


class HeatStackDriver(DriverBase):

    RESOURCE_TYPE = {
        'OS::Nova::Server': NOVA_INSTANCE_DATASOURCE,
        'OS::Cinder::Volume': CINDER_VOLUME_DATASOURCE,
        'OS::Neutron::Net': NEUTRON_NETWORK_DATASOURCE,
        'OS::Neutron::Port': NEUTRON_PORT_DATASOURCE
    }

    RESOURCE_DRIVERS = {
        'OS::Nova::Server': InstanceDriver,
        'OS::Cinder::Volume': CinderVolumeDriver,
        'OS::Neutron::Net': NetworkDriver,
        'OS::Neutron::Port': PortDriver
    }

    def __init__(self):
        super(HeatStackDriver, self).__init__()
        self._client = None
        self._filter_resource_types()

    @property
    def client(self):
        if not self._client:
            self._client = os_clients.heat_client()
        return self._client

    @staticmethod
    def get_topic():
        return CONF[HEAT_STACK_DATASOURCE].notification_topic

    @staticmethod
    def get_event_types():
        return ['orchestration.stack.create.end',
                'orchestration.stack.delete.end',
                'orchestration.stack.update.error',
                'orchestration.stack.update.end',
                'orchestration.stack.suspend.error',
                'orchestration.stack.suspend.end',
                'orchestration.stack.resume.error',
                'orchestration.stack.resume.end']

    def enrich_event(self, event, event_type):
        # TODO(Nofar): add call to get resources of the stack if not deleted
        # change transformer that if delete we remove the stack from the graph
        # and hence all the edges to it

        stack_id = event['stack_identity']
        if self._is_nested_stack(stack_id):
            return

        event[DSProps.EVENT_TYPE] = event_type
        event = self._retrieve_stack_resources(event, stack_id)

        return HeatStackDriver.make_pickleable(
            [event],
            HEAT_STACK_DATASOURCE,
            DatasourceAction.UPDATE,
            *self.properties_to_filter_out())[0]

    def _is_nested_stack(self, _id):
        return self.client.stacks.get(_id).to_dict()['parent']

    def _filter_resource_types(self):
        types = CONF.datasources.types

        self.RESOURCE_TYPE = {key: value for key, value in
                              self.RESOURCE_TYPE.items() if value in types}

    @staticmethod
    def _make_stacks_list(stacks):
        return [stack.to_dict() for stack in stacks]

    def _append_stacks_resources(self, stacks):
        return [self._retrieve_stack_resources(stack, stack['id'])
                for stack in stacks]

    @staticmethod
    def properties_to_filter_out():
        return ['manager', '_info']

    def _retrieve_stack_resources(self, stack, stack_id):
        # guess 10 is enough
        resources = self.client.resources.list(stack_id, nested_depth=10)
        stack['resources'] = [resource.to_dict() for resource in resources
                              if resource.to_dict()['resource_type'] in
                              self.RESOURCE_TYPE]
        self._filter_stack_resources(stack)
        return stack

    @staticmethod
    def _filter_stack_resources(stack):
        for resource in stack['resources']:
            props = HeatStackDriver.RESOURCE_DRIVERS[
                resource['resource_type']].properties_to_filter_out()
            for prop in props:
                if prop in resource:
                    del resource[prop]

    def get_all(self, datasource_action):
        stacks = self.client.stacks.list(global_tenant=True)
        stacks_list = self._make_stacks_list(stacks)
        stacks_with_resources = self._append_stacks_resources(stacks_list)
        for s in stacks_with_resources:
            if s['stack_status'].lower() in ['delete_complete', 'deleted',
                                             'delete_in_progress']:
                s[DSProps.EVENT_TYPE] = GraphAction.DELETE_ENTITY
        return self.make_pickleable(stacks_with_resources,
                                    HEAT_STACK_DATASOURCE,
                                    datasource_action,
                                    *self.properties_to_filter_out())

    @staticmethod
    def should_delete_outdated_entities():
        return True
