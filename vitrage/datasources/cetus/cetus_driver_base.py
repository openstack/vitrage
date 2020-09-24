# Copyright 2020 - Inspur - Qitao
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
import requests

from vitrage.keystone_client import get_auth_token
from vitrage.keystone_client import get_client
from vitrage.keystone_client import get_service_catalog

from vitrage.datasources.driver_base import DriverBase

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class CetusDriverBase(DriverBase):

    def __init__(self):
        super(CetusDriverBase, self).__init__()
        self.cetus_url = None
        self._client = None

    @property
    def client(self):
        if not self._client:
            self._client = self._get_cetus_cli()
        return self._client

    @staticmethod
    def _get_cetus_cli():
        token = get_auth_token(get_client())
        headers = dict()
        headers['Content-Type'] = 'application/json'
        headers["X-Auth-Token"] = token
        session = requests.Session()
        session.headers = headers
        return session

    @staticmethod
    def _get_cetus_url(service_name='cetusv1'):
        """modify service_name to get service endpoint url"""

        services = get_service_catalog(get_client())
        for service in services.catalog:
            if service["name"] == service_name:
                urls = [endpoint["url"] for endpoint in service["endpoints"]]
                return urls[0] if urls else None
        return None

    def get_data(self, url):
        try:
            self.cetus_url = self._get_cetus_url()
            url = '{}/{}'.format(self.cetus_url, url)
            res = self.client.get(url)
            return res.json()
        except Exception as e:
            LOG.error("Couldn't access cetus service:" + str(e))

    def list_clusters(self):
        url = "v1/clusters"
        res = self.get_data(url)
        return res

    def list_cluster_pods(self, cid):
        if not cid:
            return dict()
        url = "v1/clusters/{}/pods".format(cid)
        res = self.get_data(url)
        return res

    def list_all(self):
        pods = []
        clusters = self.list_clusters()
        for cluster in clusters.get('items', []):
            cluster_id = cluster.get("cluster_id", "")
            cluster_pods = self.list_cluster_pods(cluster_id)
            cluster_pods = cluster_pods.get("items", [])
            for pod in cluster_pods:
                pod["cluster"] = cluster
                pods.append(pod)
        return pods

    @staticmethod
    def should_delete_outdated_entities():
        return True
