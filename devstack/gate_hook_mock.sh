#!/usr/bin/env bash
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

export DEVSTACK_GATE_INSTALL_TESTONLY=1
export DEVSTACK_GATE_TEMPEST=1
export DEVSTACK_GATE_TEMPEST_NOTESTS=1
export KEEP_LOCALRC=1

DEVSTACK_LOCAL_CONFIG+=$'\nenable_plugin vitrage https://git.openstack.org/openstack/vitrage'
DEVSTACK_LOCAL_CONFIG+=$'\nenable_plugin vitrage-tempest-plugin https://git.openstack.org/openstack/vitrage-tempest-plugin'

# we don't want swift
DEVSTACK_LOCAL_CONFIG+=$'\ndisable_service s-account s-container s-object s-proxy'

DEVSTACK_LOCAL_CONFIG+="$(cat <<EOF


[[post-config|\$NOVA_CONF]]
[DEFAULT]
notification_topics = notifications,vitrage_notifications
notification_driver = messagingv2

[notifications]
versioned_notifications_topics = versioned_notifications,vitrage_notifications
notification_driver = messagingv2
notification_format = both

[[post-config|\$CINDER_CONF]]
[DEFAULT]
notification_topics = notifications,vitrage_notifications
notification_driver = messagingv2

[[post-config|\$VITRAGE_CONF]]

[DEFAULT]
verbose = true
debug = false
notifiers = nova,webhook
rpc_response_timeout=300

[datasources]
types=doctor,mock_graph_datasource
path=vitrage.datasources,vitrage.tests.mocks
snapshots_interval=60

[mock_graph_datasource]
networks=100
zones_per_cluster=4
hosts_per_zone=16
zabbix_alarms_per_host=8
instances_per_host=50
ports_per_instance=3
volumes_per_instance=2
vitrage_alarms_per_instance=0
tripleo_controllers=3
zabbix_alarms_per_controller=1
EOF
)"

export DEVSTACK_LOCAL_CONFIG
$BASE/new/devstack-gate/devstack-vm-gate.sh
