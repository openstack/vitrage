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


"""
Mock event generator.

Generator will generate events for a specific entity type, as defined
by a configuration file. A single generator can generate events for
multiple instances of the same entity type.

"""

from collections import defaultdict
from random import randint

# noinspection PyPep8Naming
from vitrage.common.constants import EdgeLabel
from vitrage.datasources.nova.host import NOVA_HOST_DATASOURCE
from vitrage.datasources.static import StaticFields
from vitrage.tests.mocks.entity_model import BasicEntityModel as Bem
import vitrage.tests.mocks.utils as utils

DYNAMIC_INFO_FKEY = 'filename'
DYNAMIC_INFO_FPATH = 'filepath'
STATIC_INFO_FKEY = 'static_filename'
NAME_KEY = 'name'
MAPPING_KEY = 'mapping'
EXTERNAL_INFO_KEY = 'external'

NUM_EVENTS = '#events'
GENERATOR = 'generator'


# specification files for input types
# Mock driver specs
MOCK_DRIVER_PATH = '%s/mock_configurations/driver' % \
    utils.get_resources_dir()
DRIVER_AODH_UPDATE_D = 'driver_aodh_update_dynamic.json'
DRIVER_DOCTOR_UPDATE_D = 'driver_doctor_update_dynamic.json'
DRIVER_COLLECTD_UPDATE_D = 'driver_collectd_update_dynamic.json'
DRIVER_KAPACITOR_UPDATE_D = 'driver_kapacitor_update_dynamic.json'
DRIVER_HOST_SNAPSHOT_D = 'driver_host_snapshot_dynamic.json'
DRIVER_INST_SNAPSHOT_D = 'driver_inst_snapshot_dynamic.json'
DRIVER_INST_SNAPSHOT_S = 'driver_inst_snapshot_static.json'
DRIVER_INST_UPDATE_LEGACY_D = 'driver_inst_update_legacy_dynamic.json'
DRIVER_INST_UPDATE_VERSIONED_D = 'driver_inst_update_versioned_dynamic.json'
DRIVER_NAGIOS_SNAPSHOT_D = 'driver_nagios_snapshot_dynamic.json'
DRIVER_NAGIOS_SNAPSHOT_S = 'driver_nagios_snapshot_static.json'
DRIVER_PROMETHEUS_UPDATE_D = 'driver_prometheus_update_dynamic.json'
DRIVER_ZABBIX_SNAPSHOT_D = 'driver_zabbix_snapshot_dynamic.json'
DRIVER_STATIC_SNAPSHOT_D = 'driver_static_snapshot_dynamic.json'
DRIVER_STATIC_SNAPSHOT_S = 'driver_static_snapshot_static.json'
DRIVER_VOLUME_UPDATE_D = 'driver_volume_update_dynamic.json'
DRIVER_VOLUME_SNAPSHOT_D = 'driver_volume_snapshot_dynamic.json'
DRIVER_STACK_UPDATE_D = 'driver_stack_update_dynamic.json'
DRIVER_STACK_SNAPSHOT_D = 'driver_stack_snapshot_dynamic.json'
DRIVER_CONSISTENCY_UPDATE_D = 'driver_consistency_update_dynamic.json'
DRIVER_ZONE_SNAPSHOT_D = 'driver_zone_snapshot_dynamic.json'
DRIVER_KUBE_SNAPSHOT_D = 'driver_kubernetes_snapshot_dynamic.json'
DRIVER_TROVE_INSTANCE_SNAPSHOT_D = \
    'driver_trove_instance_snapshot_dynamic.json'
DRIVER_TROVE_CLUSTER_SNAPSHOT_D = \
    'driver_trove_cluster_snapshot_dynamic.json'

# Mock transformer Specs (i.e., what the transformer outputs)
MOCK_TRANSFORMER_PATH = '%s/mock_configurations/transformer' % \
    utils.get_resources_dir()
TRANS_AODH_SNAPSHOT_D = 'transformer_aodh_snapshot_dynamic.json'
TRANS_AODH_UPDATE_D = 'transformer_aodh_update_dynamic.json'
TRANS_DOCTOR_UPDATE_D = 'transformer_doctor_update_dynamic.json'
TRANS_COLLECTD_UPDATE_D = 'transformer_collectd_update_dynamic.json'
TRANS_KAPACITOR_UPDATE_D = 'transformer_kapacitor_update_dynamic.json'
TRANS_PROMETHEUS_UPDATE_D = 'transformer_prometheus_update_dynamic.json'
TRANS_INST_SNAPSHOT_D = 'transformer_inst_snapshot_dynamic.json'
TRANS_HOST_SNAPSHOT_D = 'transformer_host_snapshot_dynamic.json'
TRANS_HOST_SNAPSHOT_S = 'transformer_host_snapshot_static.json'
TRANS_ZONE_SNAPSHOT_D = 'transformer_zone_snapshot_dynamic.json'
TRANS_ZONE_SNAPSHOT_S = 'transformer_zone_snapshot_static.json'


class EventTraceGenerator(object):
    """A generator for event traces.

    A generator can generate events for several instances of the same type,
    though with different static parameters (ids etc.).

    A generator generates event based on (a) dynamic content JSON file,
    (b) static content JSON file, and (c) mapping info to other entities,
    such as host-to-vm mapping.

    File is expected to be in the ../resources folder
    """

    def __init__(self, spec):
        """Initializes the trace generator according to the specs.

        NOTE: The dynamic file given determines the manner in which information
        is extracted and overlapped between the three sources of info.
        Any new spec file needs to be added here as well.

        :param spec: specification of the trace characteristics.
        :type spec: dict
        Sample format:
        {
        tg.DYNAMIC_INFO_FKEY: tg.TRANS_INST_SNAPSHOT_D, # dynamic info file
        tg.STATIC_INFO_FKEY: tg.TRANS_INST_SNAPSHOT_S, # static info file
        tg.MAPPING_KEY: mapping,  # inter-entity mapping, e.g., vm-host
        tg.NAME_KEY: 'Instance (vm) snapshot generator', # name for gen
        tg.NUM_EVENTS: 10 # how many events of this type to generate
         }
        """

        static_info_parsers = \
            {DRIVER_AODH_UPDATE_D: _get_aodh_alarm_update_driver_values,
             DRIVER_DOCTOR_UPDATE_D: _get_simple_update_driver_values,
             DRIVER_COLLECTD_UPDATE_D: _get_simple_update_driver_values,
             DRIVER_KAPACITOR_UPDATE_D: _get_simple_update_driver_values,
             DRIVER_KUBE_SNAPSHOT_D: _get_k8s_node_snapshot_driver_values,
             DRIVER_INST_SNAPSHOT_D: _get_vm_snapshot_driver_values,
             DRIVER_INST_UPDATE_LEGACY_D: _get_vm_update_legacy_driver_values,
             DRIVER_INST_UPDATE_VERSIONED_D:
                 _get_vm_update_versioned_driver_values,
             DRIVER_HOST_SNAPSHOT_D: _get_host_snapshot_driver_values,
             DRIVER_ZONE_SNAPSHOT_D: _get_zone_snapshot_driver_values,
             DRIVER_VOLUME_SNAPSHOT_D: _get_volume_snapshot_driver_values,
             DRIVER_VOLUME_UPDATE_D: _get_volume_update_driver_values,
             DRIVER_STACK_SNAPSHOT_D: _get_stack_snapshot_driver_values,
             DRIVER_STACK_UPDATE_D: _get_stack_update_driver_values,
             DRIVER_STATIC_SNAPSHOT_D: _get_static_snapshot_driver_values,
             DRIVER_NAGIOS_SNAPSHOT_D: _get_nagios_alarm_driver_values,
             DRIVER_ZABBIX_SNAPSHOT_D: _get_zabbix_alarm_driver_values,
             DRIVER_CONSISTENCY_UPDATE_D:
                 _get_consistency_update_driver_values,
             DRIVER_PROMETHEUS_UPDATE_D: _get_simple_update_driver_values,
             DRIVER_TROVE_INSTANCE_SNAPSHOT_D:
                _get_trove_instance_snapshot_driver_values,
             DRIVER_TROVE_CLUSTER_SNAPSHOT_D:
                _get_trove_cluster_snapshot_driver_values,
             TRANS_AODH_SNAPSHOT_D: _get_trans_aodh_alarm_snapshot_values,
             TRANS_AODH_UPDATE_D: _get_trans_aodh_alarm_snapshot_values,
             TRANS_DOCTOR_UPDATE_D: _get_simple_trans_alarm_update_values,
             TRANS_COLLECTD_UPDATE_D: _get_simple_trans_alarm_update_values,
             TRANS_KAPACITOR_UPDATE_D: _get_simple_trans_alarm_update_values,
             TRANS_PROMETHEUS_UPDATE_D: _get_simple_trans_alarm_update_values,
             TRANS_INST_SNAPSHOT_D: _get_trans_vm_snapshot_values,
             TRANS_HOST_SNAPSHOT_D: _get_trans_host_snapshot_values,
             TRANS_ZONE_SNAPSHOT_D: _get_trans_zone_snapshot_values}

        target_folder = spec[DYNAMIC_INFO_FPATH] \
            if spec.get(DYNAMIC_INFO_FPATH) else None
        dynam_specs = utils.load_specs(spec[DYNAMIC_INFO_FKEY],
                                       target_folder=target_folder)
        dynamic_spec_filename = spec[DYNAMIC_INFO_FKEY].split('/')[-1]
        static_specs = static_info_parsers[dynamic_spec_filename](spec)
        self.name = spec.get(NAME_KEY, 'generator')

        self._models = [Bem(dynam_specs, details) for details in static_specs]

    @property
    def models(self):
        """Returns the individual entity models for this generator.

        :return: the individual entity models for this generator.
        :rtype: list
        """

        return self._models


def generate_data_stream(models, event_num=100):
    """Generates a list of events.

    :param models:
    :param event_num: number of events to generate
    :type event_num: int
    :return: list of generated events
    :rtype: list
    """

    instance_num = len(models)
    data_stream = []
    for _ in range(event_num):
        random_model = models[randint(0, instance_num - 1)]
        data_stream.append(random_model.params)
    return data_stream


def generate_round_robin_data_stream(models, event_num=100):
    """Generates a list of events.

    :param models:
    :param event_num: number of events to generate
    :type event_num: int
    :return: list of generated events
    :rtype: list
    """

    instance_num = len(models)
    data_stream = []
    for i in range(event_num):
        next_model = models[i % instance_num]
        data_stream.append(next_model.params)
    return data_stream


def _get_vm_snapshot_driver_values(spec):
    """Generates the static driver values for each vm.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each vm.
    :rtype: list
    """

    vm_host_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []
    host_ids = {}
    for vm_name, host_name in vm_host_mapping:
        if host_name not in host_ids.keys():
            host_ids[host_name] = str(randint(0, 1000000))

        mapping = {'hostid': host_ids[host_name],
                   'hostname': host_name,
                   "OS-EXT-SRV-ATTR:host": host_name,
                   "OS-EXT-SRV-ATTR:hypervisor_hostname": host_name,
                   'name': vm_name,
                   'id': str(randint(0, 1000000)),
                   }
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_host_snapshot_driver_values(spec):
    """Generates the static driver values for each host.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each host.
    :rtype: list
    """

    host_zone_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []
    for host_name, zone_name in host_zone_mapping:

        mapping = {'host': host_name,
                   'zone': zone_name,
                   '_info': {'host_name': host_name,
                             'zone': zone_name}}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_k8s_node_snapshot_driver_values(spec):
    """Generates the static driver values for each k8s node.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each k8s node.
    :rtype: list
    """

    vm_host_mapping = spec[MAPPING_KEY]
    static_values = []
    for node_name in vm_host_mapping:
        static_values.append(combine_data(node_name, None,
                                          spec.get(EXTERNAL_INFO_KEY)))

    return static_values


def _get_simple_update_driver_values(spec):
    """Generates the static driver values for Doctor monitor notification.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of notifications of Doctor monitor
    :rtype: list
    """
    return [combine_data(None, None, spec.get(EXTERNAL_INFO_KEY, None))]


def _get_zone_snapshot_driver_values(spec):
    """Generates the static driver values for each zone.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each host.
    :rtype: list
    """

    host_zone_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []
    host_info = {
        "nova-compute": {
            "active": "True",
            "available": "False",
            "updated_at": "2016-01-05T06:39:52\\.000000"
        }
    }

    zones_info = {}
    for host_name, zone_name in host_zone_mapping:
        zone_info = zones_info.get(zone_name, {})
        zone_info[host_name] = host_info
        zones_info[zone_name] = zone_info

    for zone_name in zones_info.keys():
        mapping = {
            'zoneName': zone_name,
            'hosts': zones_info.get(zone_name, {}),
            '_info': {'zoneName': zone_name,
                      'hosts': zones_info.get(zone_name, {})
                      }
        }
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_volume_snapshot_driver_values(spec):
    """Generates the static driver values for each volume.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each volume.
    :rtype: list
    """

    volume_instance_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []

    for volume_name, instance_name in volume_instance_mapping:
        mapping = {'id': volume_name,
                   'display_name': volume_name,
                   'attachments': [{'server_id': instance_name}]}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_volume_update_driver_values(spec):
    """Generates the static driver values for each volume.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each volume.
    :rtype: list
    """

    volume_instance_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []

    for volume_name, instance_name in volume_instance_mapping:
        mapping = {'volume_id': volume_name,
                   'display_name': volume_name,
                   'volume_attachment': [{'instance_uuid': instance_name}]}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_stack_snapshot_driver_values(spec):
    """Generates the static driver values for each stack.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each stack.
    :rtype: list
    """

    stack_instance_volume_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []

    for stack_name, instance_name, volume_name \
            in stack_instance_volume_mapping:
        mapping = {'id': stack_name,
                   'stack_name': stack_name,
                   'resources': [{'resource_type': "OS::Nova::Server",
                                  'physical_resource_id': instance_name},
                                 {'resource_type': "OS::Cinder::Volume",
                                  'physical_resource_id': volume_name}]}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_stack_update_driver_values(spec):
    """Generates the static driver values for each volume.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each volume.
    :rtype: list
    """

    volume_instance_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []

    for stack_name, instance_name, volume_name in volume_instance_mapping:
        mapping = {'stack_identity': stack_name,
                   'stack_name': stack_name,
                   'resources': [{'resource_type': "OS::Nova::Server",
                                  'physical_resource_id': instance_name},
                                 {'resource_type': "OS::Cinder::Volume",
                                  'physical_resource_id': volume_name}]}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_consistency_update_driver_values(spec):
    """Generates the static driver values for each consistency event.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each consistency event.
    :rtype: list
    """

    entity_num = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []

    for i in range(entity_num):
        mapping = {}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_trans_vm_snapshot_values(spec):
    """Generates the static transformer values for each vm.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static transformer values for each vm.
    :rtype: list
    """

    vm_host_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []
    for vm_name, host_name in vm_host_mapping:
        mapping = {'hostname': host_name,
                   'id': vm_name,
                   'name': vm_name}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))

    return static_values


def _get_vm_update_legacy_driver_values(spec):
    """Generates the static driver values for each vm, for updates.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each vm updates.
    :rtype: list
    """

    vm_host_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []
    for vm_name, host_name in vm_host_mapping:
        mapping = {'payload': {'host': host_name,
                               'display_name': vm_name}}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))

    return static_values


def _get_vm_update_versioned_driver_values(spec):
    """Generates the static driver values for each vm, for updates.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each vm updates.
    :rtype: list
    """

    vm_host_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []
    for vm_name, host_name in vm_host_mapping:
        mapping = {
            'nova_object.data': {
                'host': host_name,
                'display_name': vm_name
            }

        }
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))

    return static_values


def _get_static_snapshot_driver_values(spec):
    """Generates the static driver values for static datasource.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of driver values for static datasource.
    :rtype: list
    """

    host_switch_mapping = spec[MAPPING_KEY]

    if spec[STATIC_INFO_FKEY] is not None:
        static_info_spec = utils.load_specs(spec[STATIC_INFO_FKEY])
    else:
        static_info_spec = None

    static_values = []

    # use defaultdict to create placeholder
    relationships = defaultdict(lambda: [])
    entities = defaultdict(lambda: {})
    touched = set({})

    for host_index, switch_index in host_switch_mapping:
        host_id = "h{}".format(host_index)
        switch_id = "s{}".format(switch_index)

        relationship = {
            StaticFields.SOURCE: switch_id,
            StaticFields.TARGET: host_id,
            StaticFields.RELATIONSHIP_TYPE: EdgeLabel.ATTACHED
        }
        rel = relationship.copy()
        rel[StaticFields.TARGET] = entities[host_id]
        relationships[switch_id].append(rel)

    for host_index, switch_index in host_switch_mapping:
        switch_id = "s{}".format(switch_index)
        if switch_id not in touched:
            switch_name = "switch-{}".format(switch_index)
            vals = {
                StaticFields.STATIC_ID: switch_id,
                StaticFields.TYPE: 'switch',
                StaticFields.ID: str(randint(0, 100000)),
                StaticFields.NAME: switch_name,
                StaticFields.RELATIONSHIPS: relationships[switch_id]
            }
            entities[switch_id].update(**vals)
            touched.add(switch_id)

        host_id = "h{}".format(host_index)
        if host_id not in touched:
            vals = {
                StaticFields.STATIC_ID: host_id,
                StaticFields.TYPE: NOVA_HOST_DATASOURCE,
                StaticFields.ID: str(randint(0, 100000)),
                StaticFields.RELATIONSHIPS: relationships[host_id]
            }
            entities[host_id].update(**vals)
            touched.add(host_id)

    for vals in entities.values():
        static_values.append(combine_data(static_info_spec,
                                          vals,
                                          spec.get(EXTERNAL_INFO_KEY, None)))

    custom_num = 10
    for index in range(custom_num):
        source_id = 'c{}'.format(index)
        target_id = 'c{}'.format(custom_num - 1 - index)
        source_name = 'custom-{}'.format(source_id)
        vals = {
            StaticFields.STATIC_ID: source_id,
            StaticFields.TYPE: 'custom',
            StaticFields.ID: str(randint(0, 100000)),
            StaticFields.NAME: source_name,
            StaticFields.RELATIONSHIPS: [{
                StaticFields.SOURCE: source_id,
                StaticFields.TARGET: entities[target_id],
                StaticFields.RELATIONSHIP_TYPE: 'custom'}]
        }
        entities[source_id].update(**vals)
        static_values.append(combine_data(static_info_spec,
                                          vals,
                                          spec.get(EXTERNAL_INFO_KEY, None)))

    # TODO(yujunz) verify self-pointing relationship

    return static_values


def _get_nagios_alarm_driver_values(spec):
    hosts = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])

    static_values = []
    for host_name in hosts:
        host_info = {'resource_name': host_name}
        static_values.append(combine_data(
            static_info, host_info, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_zabbix_alarm_driver_values(spec):
    hosts = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])

    static_values = []
    for host_name in hosts:
        host_info = {'resource_name': host_name}
        static_values.append(combine_data(
            static_info, host_info, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_trove_instance_snapshot_driver_values(spec):
    inst_srv_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []

    for inst_name, srv_name in inst_srv_mapping:
        mapping = {'id': inst_name,
                   'name': inst_name,
                   'server_id': srv_name}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)))
    return static_values


def _get_trove_cluster_snapshot_driver_values(spec):
    clust_inst_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []

    for clust_name, inst_name in clust_inst_mapping:
        mapping = {'id': clust_name,
                   'name': clust_name,
                   'instances': [
                       {'id': inst_name, 'name': inst_name}
                   ]}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)))
    return static_values


def _get_trans_host_snapshot_values(spec):
    """Generates the static driver values for each host.

        :param spec: specification of event generation.
        :type spec: dict
        :return: list of static driver values for each host.
        :rtype: list
        """

    host_zone_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []
    for host_name, zone_name in host_zone_mapping:
        mapping = {'zone_id': zone_name,
                   'name': host_name,
                   'id': host_name}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))

    return static_values


def _get_trans_zone_snapshot_values(spec):
    """Generates the static driver values for each zone.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of static driver values for each zone.
    :rtype: list
    """

    zone_cluster_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []
    for zone_name, cluster_name in zone_cluster_mapping:
        mapping = {'name': zone_name,
                   'id': zone_name}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))

    return static_values


def _get_trans_aodh_alarm_snapshot_values(spec):
    """Generates the dynamic transformer values for Aodh datasource.

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of dynamic transformer values for Aodh datasource.
    :rtype: list
    """

    alarm_resources_mapping = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])

    static_values = []
    for alarm_id, resource_id in alarm_resources_mapping:
        mapping = {'alarm_id': alarm_id,
                   'resource_id': resource_id,
                   'graph_query_result': [{'id': resource_id}]}
        static_values.append(combine_data(
            static_info, mapping, spec.get(EXTERNAL_INFO_KEY, None)
        ))
    return static_values


def _get_aodh_alarm_update_driver_values(spec):
    alarms = spec[MAPPING_KEY]
    static_info = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info = utils.load_specs(spec[STATIC_INFO_FKEY])
    static_values = []
    for alarm in alarms:
        alarm_id = {"alarm_id": alarm}
        static_values.append(combine_data(
            static_info, alarm_id, spec.get(EXTERNAL_INFO_KEY, None)))
    return static_values


def _get_simple_trans_alarm_update_values(spec):
    """Generates the dynamic transformer values for a simple alarm

    :param spec: specification of event generation.
    :type spec: dict
    :return: list of dynamic transformer values for a simple alarm
    :rtype: list with one alarm
    """

    static_info_re = None
    if spec[STATIC_INFO_FKEY] is not None:
        static_info_re = utils.load_specs(spec[STATIC_INFO_FKEY])

    return [combine_data(static_info_re,
                         None, spec.get(EXTERNAL_INFO_KEY, None))]


def combine_data(static_info, mapping_info, external_info):
    if external_info:
        mapping_info = utils.merge_vals(mapping_info, external_info)
    static_info = utils.generate_vals(static_info)
    return utils.merge_vals(static_info, mapping_info)


def get_trace_generators(entity_spec_list, default_events=100):
    """Returns a collection of event generators.

    :param default_events:
    :param entity_spec_list: list of generator specs.
    :type entity_spec_list: list
    :return: list of generators
    :rtype: list

    """

    generator_spec_list = \
        [
            {GENERATOR: EventTraceGenerator(entity_spec),
             NUM_EVENTS: entity_spec.get(NUM_EVENTS, default_events)}
            for entity_spec in entity_spec_list
        ]
    return generator_spec_list
