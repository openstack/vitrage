# Copyright 2015 - Alcatel-Lucent
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


"""Methods for generating driver events

For each vitrage_type of entity, need to supply configuration files that
specify (a regex of) what can be returned, which will be used to generate
driver events

usage example:
    test_entity_spec_list = [
        {mg.DYNAMIC_INFO_FKEY: 'driver_inst_snapshot_dynamic.json',
         mg.STATIC_INFO_FKEY: 'driver_inst_snapshot_static.json',
         mg.MAPPING_KEY: [('vm1', 'host1'), ('vm2', 'host1'), ('vm3','host2')],
         mg.NAME_KEY: 'Instance (vm) generator',
         NUM_EVENTS_KEY: 10
         }
    ]
    spec_list = get_mock_generators(test_entity_spec_list)
    events = generate_random_events_list(spec_list)
    for e in events:
        print e
"""

import random

from vitrage.common.constants import DatasourceAction
from vitrage.common.constants import DatasourceProperties as DSProps
import vitrage.tests.mocks.trace_generator as tg
from vitrage.utils.datetime import utcnow


def generate_random_events_list(generator_spec_list):
    """Generates random events for the generators given.

     Each element in the list of generators includes a generator and
     number of events to generate for it's entities

     :param generator_spec_list: list of generators
     :type generator_spec_list: list

     :return: list of driver events
     :rtype list

    """

    data = []
    for spec in generator_spec_list:
        generator = spec[tg.GENERATOR]
        data += tg.generate_data_stream(generator.models, spec[tg.NUM_EVENTS])
    random.shuffle(data)
    return data


def generate_sequential_events_list(generator_spec_list):
    """Generates random events for the generators given.

     Each element in the list of generators includes a generator and
     number of events to generate for it's entities

     :param generator_spec_list: list of generators
     :type generator_spec_list: list

     :return: list of driver events
     :rtype list

    """

    data = []
    for spec in generator_spec_list:
        generator = spec[tg.GENERATOR]
        data += tg.generate_round_robin_data_stream(generator.models,
                                                    spec[tg.NUM_EVENTS])
    return data


def simple_instance_generators(host_num, vm_num,
                               snapshot_events=0, update_events=0,
                               use_nova_versioned_format=True,
                               snap_vals=None, update_vals=None):
    """A function for returning vm event generators.

    Returns generators for a given number of hosts and
    instances. Instances will be distributed across hosts in round-robin style.

    :param host_num: number of hosts
    :param vm_num: number of vms
    :param snapshot_events: number of snapshot events per instance
    :param update_events: number of update events per instance
    :param use_nova_versioned_format: use the format of Nova versioned
           notifications for the update events
    :param snap_vals: preset vals for ALL snapshot events
    :param update_vals: preset vals for ALL update events
    :return: generators for vm_num vms as specified
    """

    mapping = [('vm-{0}'.format(index), 'host-{0}'.format(index % host_num))
               for index in range(vm_num)
               ]

    test_entity_spec_list = []
    if snapshot_events:
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_INST_SNAPSHOT_D,
             tg.STATIC_INFO_FKEY: tg.DRIVER_INST_SNAPSHOT_S,
             tg.EXTERNAL_INFO_KEY: snap_vals,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Instance (vm) snapshot generator',
             tg.NUM_EVENTS: snapshot_events
             }
        )

    dynamic_info = tg.DRIVER_INST_UPDATE_VERSIONED_D \
        if use_nova_versioned_format else tg.DRIVER_INST_UPDATE_LEGACY_D

    if update_events:
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: dynamic_info,
             tg.STATIC_INFO_FKEY: None,
             tg.EXTERNAL_INFO_KEY: update_vals,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Instance (vm) update generator',
             tg.NUM_EVENTS: update_events
             }
        )

    return tg.get_trace_generators(test_entity_spec_list)


def simple_host_generators(zone_num, host_num, snapshot_events=0,
                           snap_vals=None):
    """A function for returning vm event generators.

    Returns generators for a given number of hosts and
    instances. Instances will be distributed across hosts in round-robin style.

    :param zone_num: number of zones
    :param host_num: number of hosts
    :param snapshot_events: number of snapshot events per host
    :param snap_vals: preset vals for ALL snapshot events
    :return: generators for host_num hosts as specified
    """

    mapping = [('host-{0}'.format(index), 'zone-{0}'.format(index % zone_num))
               for index in range(host_num)
               ]

    test_entity_spec_list = []
    if snapshot_events:
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_HOST_SNAPSHOT_D,
             tg.STATIC_INFO_FKEY: None,
             tg.EXTERNAL_INFO_KEY: snap_vals,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Host snapshot generator',
             tg.NUM_EVENTS: snapshot_events
             }
        )
    return tg.get_trace_generators(test_entity_spec_list)


def simple_zone_generators(zone_num, host_num, snapshot_events=0,
                           snap_vals=None):
    """A function for returning zone event generators.

    Returns generators for a given number of hosts and
    zones. Hosts will be distributed across zones in round-robin style.

    :param zone_num: number of zones
    :param host_num: number of hosts
    :param snapshot_events: number of snapshot events per zone
    :param snap_vals: preset vals for ALL snapshot events
    :return: generators for zone_num zones as specified
    """

    mapping = [('host-{0}'.format(index), 'zone-{0}'.format(index % zone_num))
               for index in range(host_num)
               ]

    test_entity_spec_list = []
    if snapshot_events:
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_ZONE_SNAPSHOT_D,
             tg.STATIC_INFO_FKEY: None,
             tg.EXTERNAL_INFO_KEY: snap_vals,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Zone snapshot generator',
             tg.NUM_EVENTS: snapshot_events
             }
        )
    return tg.get_trace_generators(test_entity_spec_list)


def simple_trove_instance_generators(inst_num, snapshot_events=0,
                                     snap_vals=None):
    """A function for returning Trove instance generators.

    Returns generators for a given number of Trove instances.

    :param inst_num: number of instances
    :return: generators for inst_num instances as specified
    """

    mapping = [('tr-instance-{0}'.format(idx), 'vm-{0}'.format(idx))
               for idx in range(inst_num)]

    test_entity_spec_list = [
        {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_TROVE_INSTANCE_SNAPSHOT_D,
         tg.STATIC_INFO_FKEY: None,
         tg.MAPPING_KEY: mapping,
         tg.EXTERNAL_INFO_KEY: snap_vals,
         tg.NAME_KEY: 'Database instance snapshot generator',
         tg.NUM_EVENTS: snapshot_events
         }
    ]

    return tg.get_trace_generators(test_entity_spec_list)


def simple_trove_cluster_generators(clust_num, inst_num, snapshot_events=0,
                                    snap_vals=None):
    """A function for returning Trove cluster generators.

    Returns generators for a given number of Trove clusters.

    :param clust_num: number of clusters
    :param inst_num: number of instances
    :return: generators for clust_num clusters as specified
    """

    mapping = [('tr-cluster-{0}'.format(idx % clust_num),
                'tr-inst-{0}'.format(idx))
               for idx in range(inst_num)]

    test_entity_spec_list = [
        {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_TROVE_CLUSTER_SNAPSHOT_D,
         tg.STATIC_INFO_FKEY: None,
         tg.MAPPING_KEY: mapping,
         tg.EXTERNAL_INFO_KEY: snap_vals,
         tg.NAME_KEY: 'Database cluster snapshot generator',
         tg.NUM_EVENTS: snapshot_events
         }
    ]

    return tg.get_trace_generators(test_entity_spec_list)


def simple_volume_generators(volume_num, instance_num,
                             snapshot_events=0, update_events=0,
                             snap_vals=None, update_vals=None):
    """A function for returning vm event generators.

    Returns generators for a given number of volumes and
    instances. Instances will be distributed across hosts in round-robin style.

    :param update_vals:  number of values from update event
    :param update_events: number of events from update event
    :param volume_num: number of volumes
    :param instance_num: number of instances
    :param snapshot_events: number of snapshot events per host
    :param snap_vals: preset vals for ALL snapshot events
    :return: generators for volume_num volumes as specified
    """

    mapping = [('volume-{0}'.format(index % volume_num),
                'vm-{0}'.format(index))
               for index in range(instance_num)
               ]

    test_entity_spec_list = []
    if snapshot_events:
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_VOLUME_SNAPSHOT_D,
             tg.STATIC_INFO_FKEY: None,
             tg.EXTERNAL_INFO_KEY: snap_vals,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Volume snapshot generator',
             tg.NUM_EVENTS: snapshot_events
             }
        )
    if update_events:
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_VOLUME_UPDATE_D,
             tg.STATIC_INFO_FKEY: None,
             tg.EXTERNAL_INFO_KEY: update_vals,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Volume update generator',
             tg.NUM_EVENTS: update_events
             }
        )
    return tg.get_trace_generators(test_entity_spec_list)


def simple_stack_generators(stack_num, instance_and_volume_num,
                            snapshot_events=0, update_events=0,
                            snap_vals=None, update_vals=None):
    """A function for returning vm event generators.

    Returns generators for a given number of stacks, instances and
    volumes. Instances and Volumes will be distributed across stacks in
    round-robin style.

    :param update_vals:  number of values from update event
    :param update_events: number of events from update event
    :param stack_num: number of stacks
    :param instance_and_volume_num: number of volumes and instances
    :param snapshot_events: number of snapshot events per host
    :param snap_vals: preset vals for ALL snapshot events
    :return: generators for volume_num volumes as specified
    """

    mapping = [('stack-{0}'.format(index % stack_num),
                'stack-vm-{0}'.format(index),
                'stack-volume-{0}')
               for index in range(instance_and_volume_num)
               ]

    test_entity_spec_list = []
    if snapshot_events:
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_STACK_SNAPSHOT_D,
             tg.STATIC_INFO_FKEY: None,
             tg.EXTERNAL_INFO_KEY: snap_vals,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Stack snapshot generator',
             tg.NUM_EVENTS: snapshot_events
             }
        )
    if update_events:
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_STACK_UPDATE_D,
             tg.STATIC_INFO_FKEY: None,
             tg.EXTERNAL_INFO_KEY: update_vals,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Stack update generator',
             tg.NUM_EVENTS: update_events
             }
        )
    return tg.get_trace_generators(test_entity_spec_list)


def simple_consistency_generators(consistency_num, update_events=0,
                                  snap_vals=None, update_vals=None):
    """A function for returning consistency event generators.

    Returns generators for a given number of consistency events.
    Instances will be distributed across hosts in round-robin style.

    :param update_vals:  number of values from update event
    :param update_events: number of events from update event
    :param consistency_num: number of consistency events
    :param snap_vals: preset vals for ALL snapshot events
    :return: generators for consistency_num consistency events as specified
    """

    test_entity_spec_list = []
    if update_events:
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_CONSISTENCY_UPDATE_D,
             tg.STATIC_INFO_FKEY: None,
             tg.EXTERNAL_INFO_KEY: update_vals,
             tg.MAPPING_KEY: consistency_num,
             tg.NAME_KEY: 'Consistency update generator',
             tg.NUM_EVENTS: update_events
             }
        )
    return tg.get_trace_generators(test_entity_spec_list)


def simple_static_generators(switch_num=2, host_num=10,
                             snapshot_events=0, snap_vals=None,
                             update_events=0, update_vals=None):
    """A function for returning static datasource events generators.

    Returns generators for a given number of routers, switches and hosts.
    Hosts will be distributed across switches in round-robin style.
    Switches are interconnected in a line.

    :param switch_num: number of zones
    :param host_num: number of hosts
    :param snapshot_events: number of snapshot events per zone
    :param snap_vals: preset values for ALL snapshot events
    :param update_events: number of values from update event
    :param update_vals: preset values for update event

    :return: generators for static datasource events
    """

    # TODO(yujunz) mock routers which connects all switches
    mapping = [(host_index, host_index % switch_num)
               for host_index in range(host_num)]

    test_entity_spec_list = []
    if snapshot_events > 0:
        if snap_vals is None:
            snap_vals = {}
        snap_vals.update({
            DSProps.DATASOURCE_ACTION: DatasourceAction.SNAPSHOT,
            DSProps.SAMPLE_DATE: str(utcnow())})
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_STATIC_SNAPSHOT_D,
             tg.STATIC_INFO_FKEY: tg.DRIVER_STATIC_SNAPSHOT_S,
             tg.EXTERNAL_INFO_KEY: snap_vals,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Static snapshot generator',
             tg.NUM_EVENTS: snapshot_events
             }
        )
    if update_events > 0:
        if update_vals is None:
            update_vals = {}
        update_vals.update({
            DSProps.DATASOURCE_ACTION: DatasourceAction.UPDATE,
            DSProps.SAMPLE_DATE: str(utcnow())})
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_STATIC_SNAPSHOT_D,
             tg.STATIC_INFO_FKEY: None,
             tg.EXTERNAL_INFO_KEY: update_vals,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Static update generator',
             tg.NUM_EVENTS: update_events
             }
        )
    return tg.get_trace_generators(test_entity_spec_list)


def simple_nagios_alarm_generators(host_num,
                                   events_num=0,
                                   snap_vals=None):
    """A function for returning Nagios alarm event generators.

    Returns generators for a given number of Nagios alarms.

    :param host_num: number of hosts
    :param events_num: number of snapshot alarms per hosts
    :param snap_vals: preset vals for ALL snapshot events
    :return: generators for zone_num zones as specified
    """

    hosts = ['host-{0}'.format(index) for index in range(host_num)]

    test_entity_spec_list = []
    if events_num:
        test_entity_spec_list.append({
            tg.DYNAMIC_INFO_FKEY: tg.DRIVER_NAGIOS_SNAPSHOT_D,
            tg.STATIC_INFO_FKEY: None,
            tg.EXTERNAL_INFO_KEY: snap_vals,
            tg.MAPPING_KEY: hosts,
            tg.NAME_KEY: 'Nagios alarm generator (alarm on)',
            tg.NUM_EVENTS: max(events_num - len(hosts), 0)
        })
        test_entity_spec_list.append({
            tg.DYNAMIC_INFO_FKEY: tg.DRIVER_NAGIOS_SNAPSHOT_D,
            tg.STATIC_INFO_FKEY: tg.DRIVER_NAGIOS_SNAPSHOT_S,
            tg.EXTERNAL_INFO_KEY: snap_vals,
            tg.MAPPING_KEY: hosts,
            tg.NAME_KEY: 'Nagios alarm generator (alarm off)',
            tg.NUM_EVENTS: len(hosts)
        })

    return tg.get_trace_generators(test_entity_spec_list)


def simple_zabbix_alarm_generators(host_num,
                                   events_num=0,
                                   snap_vals=None):
    """A function for returning Zabbix alarm event generators.

    Returns generators for a given number of Zabbix alarms.

    :param host_num: number of hosts
    :param events_num: number of snapshot alarms per hosts
    :param snap_vals: preset vals for ALL snapshot events
    :return: generators for zone_num zones as specified
    """

    hosts = ['host-{0}'.format(index) for index in range(host_num)]

    test_entity_spec_list = []
    if events_num:
        test_entity_spec_list.append({
            tg.DYNAMIC_INFO_FKEY: tg.DRIVER_ZABBIX_SNAPSHOT_D,
            tg.STATIC_INFO_FKEY: None,
            tg.EXTERNAL_INFO_KEY: snap_vals,
            tg.MAPPING_KEY: hosts,
            tg.NAME_KEY: 'Zabbix alarm generator (alarm on)',
            tg.NUM_EVENTS: max(events_num - len(hosts), 0)
        })
        test_entity_spec_list.append({
            tg.DYNAMIC_INFO_FKEY: tg.DRIVER_ZABBIX_SNAPSHOT_D,
            tg.STATIC_INFO_FKEY: None,
            tg.EXTERNAL_INFO_KEY: snap_vals,
            tg.MAPPING_KEY: hosts,
            tg.NAME_KEY: 'Zabbix alarm generator (alarm off)',
            tg.NUM_EVENTS: len(hosts)
        })

    return tg.get_trace_generators(test_entity_spec_list)


def simple_doctor_alarm_generators(update_vals=None):
    """A function for returning Doctor alarm event generators.

    Returns generators for a given number of Doctor alarms.

    :param update_vals: preset values for ALL update events
    :return: generators for alarms as specified
    """

    test_entity_spec_list = [({
        tg.DYNAMIC_INFO_FKEY: tg.DRIVER_DOCTOR_UPDATE_D,
        tg.STATIC_INFO_FKEY: None,
        tg.EXTERNAL_INFO_KEY: update_vals,
        tg.MAPPING_KEY: None,
        tg.NAME_KEY: 'Doctor alarm generator',
        tg.NUM_EVENTS: 1
    })]

    return tg.get_trace_generators(test_entity_spec_list)


def simple_collectd_alarm_generators(update_vals=None):
    """A function for returning Collectd alarm event generators.

    Returns generators for a given number of Collectd alarms.

    :param update_vals: preset values for ALL update events
    :return: generators for alarms as specified
    """

    test_entity_spec_list = [({
        tg.DYNAMIC_INFO_FKEY: tg.DRIVER_COLLECTD_UPDATE_D,
        tg.STATIC_INFO_FKEY: None,
        tg.EXTERNAL_INFO_KEY: update_vals,
        tg.MAPPING_KEY: None,
        tg.NAME_KEY: 'Collectd alarm generator',
        tg.NUM_EVENTS: 1
    })]

    return tg.get_trace_generators(test_entity_spec_list)


def simple_aodh_alarm_notification_generators(alarm_num,
                                              update_events=0,
                                              update_vals=None):
    """A function for returning aodh alarm event generators.

    Returns generators for a given number of Aodh alarms.

    :param alarm_num: number of alarms
    :param update_events: number of update alarms
    :param update_vals: preset vals for ALL update events
    :return: generators for alarm_num zones as specified

    Returns generators for a given number of alarms and
    instances.
    """

    alarms = ['alarm-{0}'.format(index) for index in range(alarm_num)]

    test_entity_spec_list = [
        {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_AODH_UPDATE_D,
         tg.STATIC_INFO_FKEY: None,
         tg.MAPPING_KEY: alarms,
         tg.EXTERNAL_INFO_KEY: update_vals,
         tg.NAME_KEY: 'Aodh update generator',
         tg.NUM_EVENTS: update_events
         }
    ]

    return tg.get_trace_generators(test_entity_spec_list)


def simple_prometheus_alarm_generators(update_vals=None):
    """A function for returning Prometheus alarm event generators.

    Returns generators for a given number of Prometheus alarms.

    :param update_vals: preset values for ALL update events
    :return: generators for alarms as specified
    """

    test_entity_spec_list = [({
        tg.DYNAMIC_INFO_FKEY: tg.DRIVER_PROMETHEUS_UPDATE_D,
        tg.STATIC_INFO_FKEY: None,
        tg.EXTERNAL_INFO_KEY: update_vals,
        tg.MAPPING_KEY: None,
        tg.NAME_KEY: 'Prometheus alarm generator',
        tg.NUM_EVENTS: 1
    })]

    return tg.get_trace_generators(test_entity_spec_list)


def simple_k8s_nodes_generators(nodes_num, snapshot_events=0):
    mapping = ['vm-{0}'.format(index) for index in range(nodes_num)]

    test_entity_spec_list = []
    if snapshot_events:
        test_entity_spec_list.append(
            {tg.DYNAMIC_INFO_FKEY: tg.DRIVER_KUBE_SNAPSHOT_D,
             tg.STATIC_INFO_FKEY: tg.DRIVER_INST_SNAPSHOT_S,
             tg.MAPPING_KEY: mapping,
             tg.NAME_KEY: 'Nodes snapshot generator',
             tg.NUM_EVENTS: snapshot_events
             }
        )
    return tg.get_trace_generators(test_entity_spec_list)


def simple_kapacitor_alarm_generators(update_vals=None):
    """A function for returning Kapacitor alarm event generators.

    Returns generators for a given number of Kapacitor alarms.

    :param update_vals: preset values for ALL update events
    :return: generators for alarms as specified
    """

    test_entity_spec_list = [({
        tg.DYNAMIC_INFO_FKEY: tg.DRIVER_KAPACITOR_UPDATE_D,
        tg.STATIC_INFO_FKEY: None,
        tg.EXTERNAL_INFO_KEY: update_vals,
        tg.MAPPING_KEY: None,
        tg.NAME_KEY: 'Kapacitor alarm generator',
        tg.NUM_EVENTS: 1
    })]

    return tg.get_trace_generators(test_entity_spec_list)
