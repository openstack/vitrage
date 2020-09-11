# Copyright 2020 - Inspur - Qitao
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,  software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND,  either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from vitrage.datasources.cetus.cetus_driver_base import CetusDriverBase
from vitrage.datasources.cetus.cluster import CETUS_CLUSTER_DATASOURCE


class ClusterDriver(CetusDriverBase):

    def get_all(self, datasource_action):
        return self.make_pickleable(self._prepare_entities(
            self.list_all()),
            CETUS_CLUSTER_DATASOURCE,
            datasource_action)

    @staticmethod
    def _prepare_entities(pods):
        clusters_dict = {}
        for pod in pods:

            cluster = {
                "name": pod['cluster']["name"],
                "id": pod['cluster']["cluster_id"],
                "status": pod['cluster']["status"],
            }

            node_id = pod["metadata"]["labels"]["instance_id"]
            cluster_id = pod['cluster']["cluster_id"]
            if cluster_id not in clusters_dict:
                clusters_dict[cluster_id] = cluster
                clusters_dict[cluster_id]['nodes'] = []
            if node_id not in clusters_dict[cluster_id]['nodes']:
                clusters_dict[cluster_id]['nodes'].append(node_id)
        return [c for c in clusters_dict.values()]
