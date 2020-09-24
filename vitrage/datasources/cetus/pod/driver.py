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
from vitrage.datasources.cetus.pod import CETUS_POD_DATASOURCE


class PodDriver(CetusDriverBase):

    def get_all(self, datasource_action):
        return self.make_pickleable(self._prepare_entities(
            self.list_all()),
            CETUS_POD_DATASOURCE,
            datasource_action)

    @staticmethod
    def _prepare_entities(pods):
        pods_dict = {}
        for pod in pods:

            p = {
                "name": pod["metadata"]["name"],
                "id": pod["metadata"]["uid"],
                "status": pod["status"]["phase"],
                "node": pod["metadata"]["labels"]["instance_id"]
            }

            p_id = pod["metadata"]["uid"]
            pods_dict[p_id] = p
        return [p for p in pods_dict.values()]
