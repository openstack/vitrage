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

from collections import namedtuple


ActionSpecs = namedtuple(
    'ActionSpecs', ['id', 'type', 'targets', 'properties'])
EdgeDescription = namedtuple('EdgeDescription', ['edge', 'source', 'target'])

ENTITY = 'entity'
RELATIONSHIP = 'relationship'


class Scenario(object):
    def __init__(self, id, version, condition, actions, subgraphs, entities,
                 relationships, enabled=False):
        self.id = id
        self.version = version
        self.condition = condition
        self.actions = actions
        self.subgraphs = subgraphs
        self.entities = entities
        self.relationships = relationships
        self.enabled = enabled

    def __eq__(self, other):
        return self.id == other.id and \
            self.condition == other.condition and \
            self.actions == other.actions and \
            self.subgraphs == other.subgraphs and \
            self.entities == other.entities and \
            self.relationships == other.relationships


# noinspection PyAttributeOutsideInit
class TemplateData(object):

    def __init__(self,
                 name=None,
                 template_type=None,
                 version=None,
                 entities=None,
                 relationships=None,
                 scenarios=None):
        self.name = name
        self.template_type = template_type
        self.version = version
        self.entities = entities
        self.relationships = relationships
        self.scenarios = scenarios

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, template_name):
        self._name = template_name

    @property
    def template_type(self):
        return self._template_type

    @template_type.setter
    def template_type(self, template_type):
        self._template_type = template_type

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, version):
        self._version = version

    @property
    def entities(self):
        return self._entities

    @entities.setter
    def entities(self, entities):
        self._entities = entities

    @property
    def relationships(self):
        return self._relationships

    @relationships.setter
    def relationships(self, relationships):
        self._relationships = relationships

    @property
    def scenarios(self):
        return self._scenarios

    @scenarios.setter
    def scenarios(self, scenarios):
        self._scenarios = scenarios
