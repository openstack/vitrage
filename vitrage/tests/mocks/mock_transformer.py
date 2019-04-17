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


"""Functions for generating transformer-output events """

import random

import vitrage.tests.mocks.trace_generator as tg


def generate_random_events_list(generator_spec_list):
    """Generates random events for the generators given.

     Each element in the list of generators includes a generator and
     number of events to generate for it's entities

     :param generator_spec_list: list of generators
     :type generator_spec_list: list

     :return: list of datasource events
     :rtype list

    """

    data = []
    for spec in generator_spec_list:
        generator = spec[tg.GENERATOR]
        data += tg.generate_data_stream(generator.models, spec[tg.NUM_EVENTS])
    random.shuffle(data)
    return data


def simple_instance_generators(host_num, vm_num, snapshot_events=0,
                               snap_vals=None):
    """A simple function for returning vm generators.

    Returns generators for a given number of hosts and
    instances. Instances will be distributed across hosts in round-robin style.

    :param host_num: number of hosts
    :param vm_num: number of vms
    :param snapshot_events: number of snapshot events per instance
    :param snap_vals: number of update events per instance
    :return: generators for vm_num vms as specified
    """

    mapping = [('vm-{0}'.format(ind), 'host-{0}'.format(ind % host_num))
               for ind in range(vm_num)
               ]

    test_entity_spec_list = [
        {tg.DYNAMIC_INFO_FKEY: tg.TRANS_INST_SNAPSHOT_D,
         tg.STATIC_INFO_FKEY: tg.TRANS_INST_SNAPSHOT_S,
         tg.MAPPING_KEY: mapping,
         tg.EXTERNAL_INFO_KEY: snap_vals,
         tg.NAME_KEY: 'Instance (vm) snapshot generator',
         tg.NUM_EVENTS: snapshot_events
         }
    ]

    return tg.get_trace_generators(test_entity_spec_list)


def simple_host_generators(zone_num, host_num, snapshot_events=0,
                           snap_vals=None):
    """A simple function for returning vm generators.

    Returns generators for a given number of hosts and
    instances. Instances will be distributed across hosts in round-robin style.

    :param zone_num: number of hosts
    :param host_num: number of vms
    :param snapshot_events: number of snapshot events per instance
    :param snap_vals: number of update events per instance
    :return: generators for vm_num vms as specified
    """

    mapping = [('host-{0}'.format(ind), 'zone-{0}'.format(ind % zone_num))
               for ind in range(host_num)
               ]

    test_entity_spec_list = [
        {tg.DYNAMIC_INFO_FKEY: tg.TRANS_HOST_SNAPSHOT_D,
         tg.STATIC_INFO_FKEY: tg.TRANS_HOST_SNAPSHOT_S,
         tg.MAPPING_KEY: mapping,
         tg.EXTERNAL_INFO_KEY: snap_vals,
         tg.NAME_KEY: 'Host snapshot generator',
         tg.NUM_EVENTS: snapshot_events
         }
    ]

    return tg.get_trace_generators(test_entity_spec_list)


def simple_zone_generators(zone_num, snapshot_events=0, snap_vals=None):
    """A simple function for returning vm generators.

    Returns generators for a given number of hosts and
    instances. Instances will be distributed across hosts in round-robin style.

    :param zone_num: number of hosts
    :param snapshot_events: number of snapshot events per instance
    :param snap_vals: number of update events per instance
    :return: generators for vm_num vms as specified
    """

    mapping = [('zone-{0}'.format(ind), 'cluster-0')
               for ind in range(zone_num)]

    test_entity_spec_list = [
        {tg.DYNAMIC_INFO_FKEY: tg.TRANS_ZONE_SNAPSHOT_D,
         tg.STATIC_INFO_FKEY: tg.TRANS_ZONE_SNAPSHOT_S,
         tg.MAPPING_KEY: mapping,
         tg.EXTERNAL_INFO_KEY: snap_vals,
         tg.NAME_KEY: 'Zone snapshot generator',
         tg.NUM_EVENTS: snapshot_events
         }
    ]
    return tg.get_trace_generators(test_entity_spec_list)


def simple_aodh_alarm_generators(alarm_num,
                                 snapshot_events=0, snap_vals=None):
    """A simple function for returning aodh alarm generators.

    Returns generators for a given number of alarms.

    :param alarm_num: number of alarms
    :param snapshot_events: number of snapshot events
    :param snap_vals: values of snapshot
    :return: generators for alarm_num alarms as specified
    """

    mapping = [('alarm-{0}'.format(ind), 'resource-{0}'.format(ind))
               for ind in range(alarm_num)
               ]

    test_entity_spec_list = [
        {tg.DYNAMIC_INFO_FKEY: tg.TRANS_AODH_SNAPSHOT_D,
         tg.DYNAMIC_INFO_FPATH: tg.MOCK_TRANSFORMER_PATH,
         tg.STATIC_INFO_FKEY: None,
         tg.MAPPING_KEY: mapping,
         tg.EXTERNAL_INFO_KEY: snap_vals,
         tg.NAME_KEY: 'Aodh snapshot generator',
         tg.NUM_EVENTS: snapshot_events
         }
    ]
    return tg.get_trace_generators(test_entity_spec_list)


def simple_aodh_update_alarm_generators(alarm_num,
                                        update_events=0,
                                        update_vals=None):
    """A simple function for returning aodh alarm generators.

    Returns generators for a given number of alarms.

    :param alarm_num: number of alarms
    :param update_events: number of update events
    :param update_vals: values of update
    :return: generators for alarm_num alarms as specified
    """

    mapping = [('alarm-{0}'.format(ind), 'resource-{0}'.format(ind))
               for ind in range(alarm_num)
               ]

    test_entity_spec_list = [
        {tg.DYNAMIC_INFO_FKEY: tg.TRANS_AODH_UPDATE_D,
         tg.DYNAMIC_INFO_FPATH: tg.MOCK_TRANSFORMER_PATH,
         tg.STATIC_INFO_FKEY: None,
         tg.MAPPING_KEY: mapping,
         tg.EXTERNAL_INFO_KEY: update_vals,
         tg.NAME_KEY: 'Aodh update generator',
         tg.NUM_EVENTS: update_events
         }
    ]
    return tg.get_trace_generators(test_entity_spec_list)


def simple_doctor_alarm_generators(update_vals=None):
    """A function for returning Doctor alarm event generators.

    Returns generators for a given number of Doctor alarms.

    :param update_vals: preset values for ALL update events
    :return: generators for alarms as specified
    """
    return _simple_alarm_generators('Doctor',
                                    tg.TRANS_DOCTOR_UPDATE_D, update_vals)


def simple_collectd_alarm_generators(update_vals=None):
    """A function for returning Collectd alarm event generators.

    Returns generators for a given number of Collectd alarms.

    :param update_vals: preset values for ALL update events
    :return: generators for alarms as specified
    """
    return _simple_alarm_generators('Collectd',
                                    tg.TRANS_COLLECTD_UPDATE_D, update_vals)


def simple_kapacitor_alarm_generators(update_vals=None):
    """A function for returning Kapacitor alarm event generators.

    Returns generators for a given number of Kapacitor alarms.

    :param update_vals: preset values for ALL update events
    :return: generators for alarms as specified
    """
    return _simple_alarm_generators('Kapacitor',
                                    tg.TRANS_KAPACITOR_UPDATE_D, update_vals)


def simple_prometheus_alarm_generators(update_vals=None):
    """A function for returning Prometheus alert event generators.

    Returns generators for a given number of Prometheus alerts.

    :param update_vals: preset values for ALL update events
    :return: generators for alarms as specified
    """
    return _simple_alarm_generators('Prometheus',
                                    tg.TRANS_PROMETHEUS_UPDATE_D, update_vals)


def _simple_alarm_generators(datasource, sample_file, update_vals):
    """A function for returning alarm event generators.

    Returns generators for a given number of alarms.

    :param update_vals: preset values for ALL update events
    :return: generators for alarms as specified
    """

    test_entity_spec_list = [({
        tg.DYNAMIC_INFO_FKEY: sample_file,
        tg.DYNAMIC_INFO_FPATH: tg.MOCK_TRANSFORMER_PATH,
        tg.STATIC_INFO_FKEY: None,
        tg.EXTERNAL_INFO_KEY: update_vals,
        tg.MAPPING_KEY: None,
        tg.NAME_KEY: datasource + ' alarm generator',
        tg.NUM_EVENTS: 1
    })]

    return tg.get_trace_generators(test_entity_spec_list)
