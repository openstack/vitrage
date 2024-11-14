#!/bin/bash
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# ``upgrade-vitrage``

echo "*********************************************************************"
echo "Begin $0"
echo "*********************************************************************"

# Clean up any resources that may be in use
cleanup() {
    set +o errexit

    echo "*********************************************************************"
    echo "ERROR: Abort $0" >&2
    echo "*********************************************************************"

    # Kill ourselves to signal any calling process
    trap 2; kill -2 $$
}

trap cleanup SIGHUP SIGINT SIGTERM

# Keep track of the grenade directory
RUN_DIR=$(cd $(dirname "$0") && pwd)

# Source params
source $GRENADE_DIR/grenaderc

# Import common functions
source $GRENADE_DIR/functions

# This script exits on an error so that errors don't compound and you see
# only the first error that occurred.
set -o errexit

# Upgrade Vitrage
# ===============

# Locate vitrage devstack plugin, the directory above the
# grenade plugin.
VITRAGE_DEVSTACK_DIR=$(dirname $(dirname $0))
VITRAGE_DIR=$(dirname $(dirname $0))/../../vitrage
VITRAGE_CONF_DIR=/etc/vitrage
VITRAGE_CONF=$VITRAGE_CONF_DIR/vitrage.conf
VITRAGE_UWSGI_FILE=$VITRAGE_CONF_DIR/vitrage-uwsgi.ini
VITRAGE_PUBLIC_UWSGI=$VITRAGE_DIR/vitrage/api/app.wsgi

# Duplicate some setup bits from target DevStack
source $TARGET_DEVSTACK_DIR/functions
source $TARGET_DEVSTACK_DIR/stackrc
source $TARGET_DEVSTACK_DIR/lib/tls
source $TARGET_DEVSTACK_DIR/lib/stack
source $TARGET_DEVSTACK_DIR/lib/apache
source $TARGET_DEVSTACK_DIR/lib/rpc_backend

# Print the commands being run so that we can see the command that triggers
# an error.  It is also useful for following allowing as the install occurs.
set -o xtrace

# Save current config files for posterity
[[ -d $SAVE_DIR/etc.vitrage ]] || cp -pr $VITRAGE_CONF_DIR $SAVE_DIR/etc.vitrage

# Install the target vitrage
source $VITRAGE_DEVSTACK_DIR/plugin.sh stack install

# calls upgrade-vitrage for specific release
upgrade_project vitrage $RUN_DIR $BASE_DEVSTACK_BRANCH $TARGET_DEVSTACK_BRANCH

# do config upgrade
write_uwsgi_config "$VITRAGE_UWSGI_FILE" "$VITRAGE_PUBLIC_UWSGI" "/rca"

# Simulate init_vitrage()
VITRAGE_BIN_DIR=$(get_python_exec_prefix)
$VITRAGE_BIN_DIR/vitrage-dbsync --config-file $VITRAGE_CONF || die $LINENO "DB sync error"

# Start Vitrage
start_vitrage

# Don't succeed unless the services come up
# Truncating some service names to 11 characters
ensure_services_started vitrage-api vitrage-graph vitrage-notifier vitrage-ml vitrage-persistor vitrage-snmp-parsing

set +o xtrace
echo "*********************************************************************"
echo "SUCCESS: End $0"
echo "*********************************************************************"
