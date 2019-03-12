# Copyright 2016 - Nokia, ZTE
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR  CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from vitrage.common.constants import DatasourceOpts as DSOpts
from vitrage.common.constants import UpdateMethod

STATIC_DATASOURCE = 'static'

OPTS = [
    cfg.StrOpt(DSOpts.TRANSFORMER,
               default='vitrage.datasources.static.transformer.'
                       'StaticTransformer',
               help='Static transformer class path',
               required=True),
    cfg.StrOpt(DSOpts.DRIVER,
               default='vitrage.datasources.static.driver.'
                       'StaticDriver',
               help='Static driver class path',
               required=True),
    cfg.StrOpt(DSOpts.UPDATE_METHOD,
               default=UpdateMethod.PULL,
               help='None: updates only via Vitrage periodic snapshots.'
                    'Pull: updates periodically.'
                    'Push: updates by getting notifications from the'
                    ' datasource itself.',
               required=True),
    cfg.IntOpt(DSOpts.CHANGES_INTERVAL,
               default=30,
               min=10,
               help='interval in seconds between checking changes in the'
                    'static configuration files'),
    cfg.StrOpt('directory', default='/etc/vitrage/static_datasources',
               help='static data sources configuration directory')]


STATIC_SCHEMA = {
    "type": "object",
    "required": ["definitions"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {
                    "type": "string",
                },
                "description": {
                    "type": "string",
                },
            }
        },
        "definitions": {
            "type": "object",
            "required": ["entities", "relationships"],
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["static_id"],
                        "properties": {
                            "static_id": {
                                "type": "string",
                            },
                            "type": {
                                "type": "string",
                            },
                            "name": {
                                "type": "string",
                            },
                            "id": {
                                "type": "string",
                            },
                            "state": {
                                "type": "string",
                            },
                        },
                    },
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["source", "target",
                                     "relationship_type"],
                        "properties": {
                            "source": {
                                "type": "string",
                            },
                            "target": {
                                "type": "string",
                            },
                            "relationship_type": {
                                "type": "string",
                            },
                        },
                    },
                },
            }
        },
    },
}


class StaticFields(object):
    """yaml fields for static definitions"""
    METADATA = 'metadata'
    DEFINITIONS = 'definitions'
    RELATIONSHIPS = 'relationships'
    ENTITIES = 'entities'
    RELATIONSHIP_TYPE = 'relationship_type'
    SOURCE = 'source'
    TARGET = 'target'
    STATIC_ID = 'static_id'
    TYPE = 'type'
    CATEGORY = 'category'
    ID = 'id'
    NAME = 'name'
    STATE = 'state'
