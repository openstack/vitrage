# Copyright 2020
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
from oslo_log import log

from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.utils import file as file_utils

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class TmfApi639Config(object):
    def __init__(self):
        try:
            tmfapi639_config_file = CONF.tmfapi639[DSOpts.CONFIG_FILE]
            tmfapi639_config = file_utils.load_yaml_file(tmfapi639_config_file)
            self.endpoints = self._create_mapping(tmfapi639_config)
        except Exception as e:
            LOG.error("Failed initialization: " + str(e))
            self.endpoints = []

    @staticmethod
    def _create_mapping(config):
        """Read URL list from config dictionary"""
        LOG.debug(config)
        endpoint_list = []
        # Tuple list containing either 1 or 2 elements (Endpoint and updates)
        for e in config:
            snapshot_url = e["endpoint"]["snapshot"]
            update_url = ""
            if "update" in e["endpoint"]:
                update_url = e["endpoint"]["update"]
            if update_url != "":
                endpoint_list.append((snapshot_url, update_url))
            else:
                endpoint_list.append(snapshot_url)
        LOG.info("Finished reading endpoints file")
        return endpoint_list
