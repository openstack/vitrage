# Install and start **Vitrage** service in devstack
#
# To enable vitrage behavior add an entry to local.conf that
# looks like
#
# [[local|localrc]]
# enable_plugin vitrage https://opendev.org/openstack/vitrage
#
# By default all vitrage services are started (see
# devstack/settings).
#

# Defaults
# --------
GITDIR["python-vitrageclient"]=$DEST/python-vitrageclient
GITREPO["python-vitrageclient"]=${VITRAGECLIENT_REPO:-${GIT_BASE}/openstack/python-vitrageclient.git}
GITBRANCH["vitrage"]=${VITRAGE_BRANCH:-$TARGET_BRANCH}
GITBRANCH["python-vitrageclient"]=${VITRAGECLIENT_BRANCH:-$TARGET_BRANCH}

# Support potential entry-points console scripts in VENV or not
if [[ ${USE_VENV} = True ]]; then
    PROJECT_VENV["vitrage"]=${VITRAGE_DIR}.venv
    VITRAGE_BIN_DIR=${PROJECT_VENV["vitrage"]}/bin
else
    VITRAGE_BIN_DIR=$(get_python_exec_prefix)
fi

# VITRAGE_DEPLOY defines how vitrage is deployed, allowed values:
# - mod_wsgi : Run vitrage under Apache HTTPd mod_wsgi
# - uwsgi : Run vitrage under uwsgi
if [[ "$WSGI_MODE" == "uwsgi" ]]; then
    VITRAGE_DEPLOY=${VITRAGE_DEPLOY:-uwsgi}
else
    VITRAGE_DEPLOY=${VITRAGE_DEPLOY:-mod_wsgi}
fi

# Test if any Vitrage services are enabled
# is_vitrage_enabled
function is_vitrage_enabled {
    [[ ,${ENABLED_SERVICES} =~ ,"vitrage-" ]] && return 0
    return 1
}

function vitrage_service_url {
    if [[ "$VITRAGE_DEPLOY" == "mod_wsgi" ]]; then
       echo "$VITRAGE_SERVICE_PROTOCOL://$VITRAGE_SERVICE_HOST:$VITRAGE_SERVICE_PORT"
    else
       echo "$VITRAGE_SERVICE_PROTOCOL://$VITRAGE_SERVICE_HOST/rca"
    fi
}


# Configure mod_wsgi
function _vitrage_config_apache_wsgi {
    sudo mkdir -p $VITRAGE_WSGI_DIR

    local vitrage_apache_conf=$(apache_site_config_for vitrage)
    local venv_path=""

    # Copy proxy vhost and wsgi file
    sudo cp $VITRAGE_DIR/vitrage/api/app.wsgi $VITRAGE_WSGI_DIR/app

    if [[ ${USE_VENV} = True ]]; then
        venv_path="python-path=${PROJECT_VENV["vitrage"]}/lib/$(python_version)/site-packages"
    fi

    sudo cp $VITRAGE_DIR/devstack/apache-vitrage.template $vitrage_apache_conf

    sudo sed -e "
        s|%PORT%|$VITRAGE_SERVICE_PORT|g;
        s|%APACHE_NAME%|$APACHE_NAME|g;
        s|%WSGIAPP%|$VITRAGE_WSGI_DIR/app|g;
        s|%USER%|$STACK_USER|g;
        s|%APIWORKERS%|$API_WORKERS|g;
        s|%VIRTUALENV%|$venv_path|g
    " -i $vitrage_apache_conf
}


# Create vitrage related accounts in Keystone
function _vitrage_create_accounts {
    if is_service_enabled vitrage-api; then

        get_or_create_user "vitrage" "$ADMIN_PASSWORD" "$ADMIN_DOMAIN_NAME"
        get_or_add_user_project_role "admin" "vitrage" "$SERVICE_PROJECT_NAME" "$SERVICE_DOMAIN_NAME" "$SERVICE_DOMAIN_NAME"
        get_or_add_user_project_role "admin" "vitrage" "admin" "$ADMIN_DOMAIN_NAME" "$ADMIN_DOMAIN_NAME"

        local vitrage_service=$(get_or_create_service "vitrage" \
            "rca" "Root Cause Analysis Service")
        get_or_create_endpoint $vitrage_service \
            "$REGION_NAME" \
            "$(vitrage_service_url)" \
            "$(vitrage_service_url)" \
            "$(vitrage_service_url)"
    fi
}

# Activities to do before vitrage has been installed.
function preinstall_vitrage {
    # Nothing for now
    :
}

# Remove WSGI files, disable and remove Apache vhost file
function _vitrage_cleanup_apache_wsgi {
    sudo rm -f $VITRAGE_WSGI_DIR/*
    sudo rm -f $(apache_site_config_for vitrage)
}

# cleanup_vitrage() - Remove residual data files, anything left over
# from previous runs that a clean run would need to clean up
function cleanup_vitrage {
    if [[ "$VITRAGE_DEPLOY" == "mod_wsgi" ]]; then
        _vitrage_cleanup_apache_wsgi
    else
       remove_uwsgi_config "$VITRAGE_UWSGI_FILE" "$VITRAGE_PUBLIC_UWSGI"
    fi

    # delete all vitrage configurations
    sudo rm -rf /etc/vitrage/*
}

function disable_vitrage_datasource {

    local enabled_datasources=",${VITRAGE_DEFAULT_DATASOURCES},"
    local datasource
    for datasource in $@; do
            enabled_datasources=${enabled_datasources//,$datasource,/,}
    done
    VITRAGE_DEFAULT_DATASOURCES=$(_cleanup_service_list "$enabled_datasources")

}

# Set configuration for database backend.
function vitrage_configure_db_backend {
    if [[ "$VITRAGE_DATABASE" = 'mysql' ]] || [[ "$VITRAGE_DATABASE" = 'postgresql' ]] ; then
        iniset $VITRAGE_CONF database connection $(database_connection_url vitrage)
    else
        die $LINENO "Unable to configure unknown VITRAGE_DATABASE $VITRAGE_DATABASE"
    fi
}

# Configure Vitrage
function configure_vitrage {
    iniset_rpc_backend vitrage $VITRAGE_CONF

    iniset $VITRAGE_CONF DEFAULT debug "$ENABLE_DEBUG_LOG_LEVEL"

    # Set up logging
    if [[ "$SYSLOG" != "False" ]]; then
        iniset $VITRAGE_CONF DEFAULT use_syslog "True"
    fi

    # Format logging
    setup_logging $VITRAGE_CONF

    cp $VITRAGE_DIR/etc/vitrage/api-paste.ini $VITRAGE_CONF_DIR

    # Service credentials - openstack clients using keystone
    iniset $VITRAGE_CONF service_credentials auth_type password
    iniset $VITRAGE_CONF service_credentials username vitrage
    iniset $VITRAGE_CONF service_credentials user_domain_id default
    iniset $VITRAGE_CONF service_credentials project_domain_id default
    iniset $VITRAGE_CONF service_credentials password $ADMIN_PASSWORD
    iniset $VITRAGE_CONF service_credentials project_name admin
    iniset $VITRAGE_CONF service_credentials region_name $REGION_NAME
    iniset $VITRAGE_CONF service_credentials auth_url $KEYSTONE_SERVICE_URI

    # Configured db
    vitrage_configure_db_backend

    # remove neutron vitrage datasource if neutron datasource not installed
    if ! is_service_enabled neutron; then
        disable_vitrage_datasource neutron.network neutron.port
    fi

    # remove aodh vitrage datasource if aodh datasource not installed
    if ! is_service_enabled aodh; then
        disable_vitrage_datasource aodh
    fi

    # remove heat vitrage datasource if heat datasource not installed
    if ! is_service_enabled heat; then
        disable_vitrage_datasource heat.stack
    fi

    # remove trove vitrage datasource if trove datasource not installed
    if ! is_service_enabled trove; then
        disable_vitrage_datasource trove.instance trove.cluster
    fi

    # remove monasca vitrage datasource if nagios datasource not installed
    if ! is_service_enabled monasca; then
        disable_vitrage_datasource monasca
    fi

    # remove nagios vitrage datasource if nagios datasource not installed
    if [[ "$VITRAGE_USE_NAGIOS" == "False" ]]; then
        disable_vitrage_datasource nagios
    fi

    # remove static vitrage datasource if it's not enabled
    if [[ "$VITRAGE_USE_STATIC" == "False" ]]; then
        disable_vitrage_datasource static
    fi

    # remove doctor vitrage datasource if it's not enabled
    if [[ "$VITRAGE_USE_DOCTOR" == "False" ]]; then
        disable_vitrage_datasource doctor
    fi

    # remove prometheus vitrage datasource if it's not enabled
    if [[ "$VITRAGE_USE_PROMETHEUS" == "False" ]]; then
        disable_vitrage_datasource prometheus
    fi

    # add default datasources
    iniset $VITRAGE_CONF datasources types $VITRAGE_DEFAULT_DATASOURCES

    # create some folders
    mkdir -p $VITRAGE_CONF_DIR/datasources_values
    mkdir -p $VITRAGE_CONF_DIR/static_datasources

    # copy datasources
    cp $VITRAGE_DIR/etc/vitrage/datasources_values/*.yaml $VITRAGE_CONF_DIR/datasources_values

    configure_auth_token_middleware $VITRAGE_CONF vitrage $VITRAGE_AUTH_CACHE_DIR

    iniset $VITRAGE_CONF "keystone_authtoken" password $ADMIN_PASSWORD
    iniset $VITRAGE_CONF "keystone_authtoken" user_domain_name $admin_domain_name
    iniset $VITRAGE_CONF "keystone_authtoken" project_name $admin_project_name
    iniset $VITRAGE_CONF "keystone_authtoken" project_domain_name $admin_domain_name

    if [[ "$VITRAGE_DEPLOY" == "mod_wsgi" ]]; then
        _vitrage_config_apache_wsgi
    else
        write_uwsgi_config "$VITRAGE_UWSGI_FILE" "$VITRAGE_PUBLIC_UWSGI" "/rca"
    fi

    if [[ ! -z "$VITRAGE_COORDINATION_URL" ]]; then
        iniset $VITRAGE_CONF coordination backend_url "$VITRAGE_COORDINATION_URL"
    elif is_service_enabled etcd3; then
        iniset $VITRAGE_CONF coordination backend_url "etcd3+http://${SERVICE_HOST}:$ETCD_PORT"
    fi

    iniset $VITRAGE_CONF DEFAULT "executor_thread_pool_size" 1
}

# init_vitrage() - Initialize etc.
function init_vitrage {
    # Get vitrage keystone settings in place
    _vitrage_create_accounts

    # Create and upgrade database only when used
    if is_service_enabled mysql postgresql; then
        if [[ "$VITRAGE_DATABASE" = 'mysql' ]] || [[ "$VITRAGE_DATABASE" = 'postgresql' ]] ; then
            recreate_database vitrage
            $VITRAGE_BIN_DIR/vitrage-dbsync
        fi
    fi
    # Create cache dir
    sudo install -d -o $STACK_USER $VITRAGE_AUTH_CACHE_DIR
    rm -f $VITRAGE_AUTH_CACHE_DIR/*

}

# Install Vitrage.
function install_vitrage {
    install_vitrageclient
    setup_develop "$VITRAGE_DIR" openstack
    sudo install -d -o $STACK_USER -m 755 $VITRAGE_CONF_DIR

    if [[ "$VITRAGE_DEPLOY" == "mod_wsgi" ]]; then
        install_apache_wsgi
    fi
}

# install_vitrageclient()
function install_vitrageclient {
    if use_library_from_git "python-vitrageclient"; then
        git_clone_by_name "python-vitrageclient"
        setup_dev_lib "python-vitrageclient"
        sudo install -D -m 0644 -o $STACK_USER {${GITDIR["python-vitrageclient"]}/tools/,/etc/bash_completion.d/}vitrage.bash_completion
    else
        pip_install_gr python-vitrageclient
    fi
}

# start_vitrage() - Start running processes
function start_vitrage {
    if [[ "$VITRAGE_DEPLOY" == "mod_wsgi" ]]; then
        enable_apache_site vitrage
        restart_apache_server
    elif [[ "$VITRAGE_DEPLOY" == "uwsgi" ]]; then
        run_process vitrage-api "$(which uwsgi) --procname-prefix vitrage --ini $VITRAGE_UWSGI_FILE" ""
    else
        run_process vitrage-api "$VITRAGE_BIN_DIR/vitrage-api -d -v --config-file $VITRAGE_CONF"
    fi

    # Only die on API if it was actually intended to be turned on
    if is_service_enabled vitrage-api; then
        echo "Waiting for vitrage-api to start..."
        if ! wait_for_service $SERVICE_TIMEOUT $(vitrage_service_url)/v1/; then
            die $LINENO "vitrage-api did not start"
        fi
    fi

    run_process vitrage-graph "$VITRAGE_BIN_DIR/vitrage-graph --config-file $VITRAGE_CONF"
    run_process vitrage-notifier "$VITRAGE_BIN_DIR/vitrage-notifier --config-file $VITRAGE_CONF"
    run_process vitrage-ml "$VITRAGE_BIN_DIR/vitrage-ml --config-file $VITRAGE_CONF"
    run_process vitrage-persistor "$VITRAGE_BIN_DIR/vitrage-persistor --config-file $VITRAGE_CONF"
    run_process vitrage-snmp-parsing "$VITRAGE_BIN_DIR/vitrage-snmp-parsing --config-file $VITRAGE_CONF"


    change_systemd_kill_mode vitrage-graph
}


function change_systemd_kill_mode {
   local service=$1
   local systemd_service="devstack@$service.service"
   local unitfile="$SYSTEMD_DIR/$systemd_service"

   iniset -sudo $unitfile "Service" "KillMode" "control-group"

   $SYSTEMCTL daemon-reload
}

# stop_vitrage() - Stop running processes
function stop_vitrage {
    if [[ "$VITRAGE_DEPLOY" == "mod_wsgi" ]]; then
        disable_apache_site vitrage
        restart_apache_server
    fi
    for serv in vitrage-api vitrage-graph vitrage-notifier vitrage-persistor vitrage-ml vitrage-snmp-parsing; do
        stop_process $serv
    done
}

function modify_heat_global_index_policy_rule {
    if is_service_enabled heat; then
        local heat_policy=/etc/heat/policy.yaml
        touch $heat_policy
        # List stacks globally.
        # GET  /v1/{tenant_id}/stacks
        echo '"stacks:global_index": "rule:deny_stack_user"' >> $heat_policy
    fi
}

function add_monasca_rule_to_vitrage {
    if is_service_enabled monasca; then
       get_or_add_user_project_role "monasca-read-only-user" "vitrage" "admin"
    fi
}

# This is the main for plugin.sh
if is_service_enabled vitrage; then
    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        # Set up other services
        echo_summary "Configuring system services for Vitrage"
        preinstall_vitrage
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing Vitrage"
        # Use stack_install_service here to account for virtualenv
        stack_install_service vitrage
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring Vitrage"
        configure_vitrage
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Initializing Vitrage"
        # enable global index
        modify_heat_global_index_policy_rule
        # Tidy base for vitrage
        init_vitrage
        # add monasca-read-only-user role to vitrage user so
        # vitrage user can read monasca alarms
        add_monasca_rule_to_vitrage
        # Start the services
        start_vitrage
    fi

    if [[ "$1" == "unstack" ]]; then
        echo_summary "Shutting Down Vitrage"
        stop_vitrage
    fi

    if [[ "$1" == "clean" ]]; then
        echo_summary "Cleaning Vitrage"
        cleanup_vitrage
    fi
fi
