#!/usr/bin/env bash
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

export DEVSTACK_GATE_NEUTRON=1
export DEVSTACK_GATE_HEAT=1
export DEVSTACK_GATE_INSTALL_TESTONLY=1
export DEVSTACK_GATE_TEMPEST=1
export DEVSTACK_GATE_TEMPEST_NOTESTS=1
export KEEP_LOCALRC=1

DEVSTACK_LOCAL_CONFIG+=$'\nenable_plugin heat https://git.openstack.org/openstack/heat'
DEVSTACK_LOCAL_CONFIG+=$'\nenable_plugin ceilometer https://git.openstack.org/openstack/ceilometer'
DEVSTACK_LOCAL_CONFIG+=$'\nenable_plugin aodh https://git.openstack.org/openstack/aodh'
DEVSTACK_LOCAL_CONFIG+=$'\nenable_plugin mistral https://git.openstack.org/openstack/mistral'
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

[[post-config|\$NEUTRON_CONF]]
[DEFAULT]
notification_topics = notifications,vitrage_notifications
notification_driver = messagingv2

[[post-config|\$CINDER_CONF]]
[DEFAULT]
notification_topics = notifications,vitrage_notifications
notification_driver = messagingv2

[[post-config|\$HEAT_CONF]]
[DEFAULT]
notification_topics = notifications,vitrage_notifications
notification_driver = messagingv2
policy_file = /etc/heat/policy.yaml

[[post-config|\$AODH_CONF]]
[oslo_messaging_notifications]
driver = messagingv2
topics = notifications, vitrage_notifications

[[post-config|\$VITRAGE_CONF]]

[DEFAULT]
notifiers = mistral,nova,webhook

[datasources]
snapshots_interval = 120
EOF
)"

export DEVSTACK_LOCAL_CONFIG
$BASE/new/devstack-gate/devstack-vm-gate.sh
