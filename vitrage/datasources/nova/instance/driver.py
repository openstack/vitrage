# Copyright 2016 - Alcatel-Lucent
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,  software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND,  either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.constants import GraphAction
from vitrage.datasources.nova.instance import NOVA_INSTANCE_DATASOURCE
from vitrage.datasources.nova.nova_driver_base import NovaDriverBase


CONF = cfg.CONF

# versioned notifications
VERSIONED_NOTIFICATIONS = {
    'instance.create.end',
    'instance.create.error',
    'instance.delete.end',
    'instance.delete.start',
    'instance.evacuate',
    'instance.interface_attach.end',
    'instance.interface_attach.error',
    'instance.interface_detach.end',
    'instance.live_migration_abort.end',
    'instance.live_migration_force_complete.end',
    'instance.live_migration_post.end',
    'instance.live_migration_post_dest.end',
    'instance.live_migration_rollback.end',
    'instance.live_migration_rollback_dest.end',
    'instance.lock',
    'instance.pause.end',
    'instance.power_off.end',
    'instance.power_on.end',
    'instance.reboot.end',
    'instance.reboot.error',
    'instance.rebuild.end',
    'instance.rebuild.error',
    'instance.rescue.end',
    'instance.resize.end',
    'instance.resize.error',
    'instance.resize_confirm.end',
    'instance.resize_finish.end',
    'instance.resize_prep.end',
    'instance.resize_revert.end',
    'instance.restore.end',
    'instance.resume.end',
    'instance.shelve.end',
    'instance.shelve_offload.end',
    'instance.shutdown.end',
    'instance.soft_delete.end',
    'instance.snapshot.end',
    'instance.suspend.end',
    'instance.unlock',
    'instance.unpause.end',
    'instance.unrescue.end',
    'instance.unshelve.end',
    'instance.update',
    'instance.volume_attach.end',
    'instance.volume_attach.error',
    'instance.volume_detach.end',
    'instance.volume_swap.end',
    'instance.volume_swap.error',
}

# legacy (unversioned) notifications
LEGACY_NOTIFICATIONS = {
    'compute.instance.create.error',
    'compute.instance.create.end',
    'compute.instance.delete.start',
    'compute.instance.delete.end',
    'compute.instance.finish_resize.end',
    'compute.instance.live_migration.post.dest.end',
    'compute.instance.live_migration._post.end',
    'compute.instance.power_off.end',
    'compute.instance.power_on.end',
    'compute.instance.reboot.end',
    'compute.instance.rebuild.end',
    'compute.instance.resize.end',
    'compute.instance.resize.revert.end',
    'compute.instance.resume.end',
    'compute.instance.shutdown.end',
    'compute.instance.suspend.end',
    'compute.instance.volume.attach',
    'compute.instance.volume.detach',
    'compute.instance.pause.end',
    'compute.instance.unpause.end'
}


class InstanceDriver(NovaDriverBase):

    @staticmethod
    def extract_events(instances):
        events = [vars(instance) for instance in instances]
        for e in events:
            if e['status'].lower() == 'deleted':
                e[DSProps.EVENT_TYPE] = GraphAction.DELETE_ENTITY
        return events

    def get_all(self, datasource_action):
        return self.make_pickleable(
            self.extract_events(self.client.servers.list(
                search_opts={'all_tenants': 1})),
            NOVA_INSTANCE_DATASOURCE,
            datasource_action,
            *self.properties_to_filter_out())

    def enrich_event(self, event, event_type):
        use_versioned = CONF.use_nova_versioned_notifications

        # Send to the processor only events of the matching types. Nova may
        # send both versioned and legacy notifications, and we don't want to
        # handle a similar event twice.
        if (use_versioned and event_type in VERSIONED_NOTIFICATIONS) or \
                ((not use_versioned) and event_type in LEGACY_NOTIFICATIONS):
            event[DSProps.EVENT_TYPE] = event_type
            return InstanceDriver.make_pickleable([event],
                                                  NOVA_INSTANCE_DATASOURCE,
                                                  DatasourceAction.UPDATE)[0]

        return []

    @staticmethod
    def properties_to_filter_out():
        return ['manager', 'OS-EXT-SRV-ATTR:user_data', '_info']

    @staticmethod
    def get_event_types():
        return list(VERSIONED_NOTIFICATIONS | LEGACY_NOTIFICATIONS)

    @staticmethod
    def should_delete_outdated_entities():
        return True
