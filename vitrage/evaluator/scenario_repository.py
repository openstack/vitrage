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
from collections import defaultdict
from collections import namedtuple

import itertools
from oslo_log import log

from vitrage.common.constants import TemplateStatus
from vitrage.common.constants import TemplateTypes as TType
from vitrage.common.utils import get_portion
from vitrage.evaluator.base import get_template_schema
from vitrage.evaluator.base import Template
from vitrage.evaluator.base import TEMPLATE_LOADER
from vitrage.evaluator.equivalence_repository import EquivalenceRepository
from vitrage.evaluator.template_loading.scenario_loader import ScenarioLoader
from vitrage.graph.filter import check_filter as check_subset
from vitrage import storage

LOG = log.getLogger(__name__)

EdgeKeyScenario = namedtuple('EdgeKeyScenario', ['label', 'source', 'target'])
DEF_TEMPLATES_DIR_OPT = 'def_templates_dir'


class ScenarioRepository(object):
    def __init__(self, worker_index=None, workers_num=None):
        """Create an instance of ScenarioRepository

        :param conf:
        :param worker_index: Index of the current evaluator worker
        :param workers_num: Total number of evaluator workers
        """
        self._templates = {}
        self._def_templates = {}
        self._all_scenarios = []
        self._db = storage.get_connection_from_config()
        self.entity_equivalences = EquivalenceRepository().load(self._db)
        self.relationship_scenarios = defaultdict(list)
        self.entity_scenarios = defaultdict(list)
        self._load_def_templates_from_db()
        self._load_templates_from_db()
        self._enable_worker_scenarios(worker_index, workers_num)
        self.actions = self._create_actions_collection()

    @property
    def templates(self):
        return self._templates

    @property
    def def_templates(self):
        return self._def_templates

    @def_templates.setter
    def def_templates(self, def_templates):
        self._def_templates = def_templates

    @templates.setter
    def templates(self, templates):
        self._templates = templates

    def get_scenarios_by_vertex(self, vertex):

        entity_key = vertex.properties

        scenarios = []
        for scenario_key, value in self.entity_scenarios.items():
            if check_subset(entity_key, dict(scenario_key)):
                scenarios += [(e, s) for e, s in value if s.enabled]
        return scenarios

    def get_scenarios_by_edge(self, edge_description):

        key = self._create_edge_scenario_key(edge_description)
        scenarios = []

        for scenario_key, value in self.relationship_scenarios.items():

            check_label = key.label == scenario_key.label
            if check_label \
                    and check_subset(dict(key.source),
                                     dict(scenario_key.source)) \
                    and check_subset(dict(key.target),
                                     dict(scenario_key.target)):
                scenarios += [(e, s) for e, s in value if s.enabled]

        return scenarios

    def _add_template(self, template):
        self.templates[template.uuid] = Template(template.uuid,
                                                 template.file_content,
                                                 template.created_at)
        schema = get_template_schema(template.file_content)
        template_data = schema.loaders[TEMPLATE_LOADER].load(
            schema,
            template.file_content,
            self._def_templates)
        for scenario in template_data.scenarios:
            for equivalent_scenario in self._expand_equivalence(scenario):
                self._add_scenario(equivalent_scenario)

    def _add_def_template(self, def_template):
        self.def_templates[def_template.uuid] = Template(
            def_template.uuid,
            def_template.file_content,
            def_template.created_at)

    def _expand_equivalence(self, scenario):
        equivalent_scenarios = [scenario]
        for symbol_name, entity in scenario.entities.items():
            entity_key = frozenset(entity.properties.items())
            if entity_key not in self.entity_equivalences:
                continue
            equivalent_scenarios = self._expand_on_symbol(
                equivalent_scenarios,
                symbol_name,
                self.entity_equivalences[entity_key] - {entity_key})
        return equivalent_scenarios

    @staticmethod
    def _expand_on_symbol(scenarios_in, symbol_name, entity_keys):
        scenarios_out = list(scenarios_in)
        for entity_key in entity_keys:
            for scenario in scenarios_in:
                equivalent_scenario = \
                    ScenarioLoader.build_equivalent_scenario(scenario,
                                                             symbol_name,
                                                             entity_key)
                scenarios_out.append(equivalent_scenario)
        return scenarios_out

    def _add_scenario(self, scenario):
        for entity in scenario.entities.values():
            self._add_entity_scenario(scenario, entity)
        for relationship in scenario.relationships.values():
            self._add_relationship_scenario(scenario, relationship)
        self._all_scenarios.append(scenario)

    def _load_def_templates_from_db(self):
        def_templates = self._db.templates.query(
            template_type=TType.DEFINITION,
            status=TemplateStatus.ACTIVE)
        for def_template in def_templates:
            self._add_def_template(def_template)

    def _load_templates_from_db(self):
        items = self._db.templates.query(template_type=TType.STANDARD)
        # TODO(ikinory): statuses may cause loading templates to be running
        templates = [x for x in items if x.status in [TemplateStatus.ACTIVE,
                                                      TemplateStatus.LOADING,
                                                      TemplateStatus.DELETING]]
        for t in templates:
            self._add_template(t)

    @staticmethod
    def _create_scenario_key(properties):
        return frozenset(properties)

    def _add_relationship_scenario(self, scenario, edge_desc):

        key = self._create_edge_scenario_key(edge_desc)
        self.relationship_scenarios[key].append((edge_desc, scenario))

    @staticmethod
    def _create_edge_scenario_key(edge_desc):
        try:
            source_set = frozenset(edge_desc.source.properties.items())
            target_set = frozenset(edge_desc.target.properties.items())
        except Exception as e:
            LOG.error('frozenset for edge failed - Source:%s Target:%s',
                      edge_desc.source,
                      edge_desc.target)
            raise e
        return EdgeKeyScenario(edge_desc.edge.label, source_set, target_set)

    def _add_entity_scenario(self, scenario, entity):

        key = frozenset(list(entity.properties.items()))
        self.entity_scenarios[key].append((entity, scenario))

    def _enable_worker_scenarios(self, worker_ind, n):
        """Enable a portion of the scenarios"""
        self._all_scenarios.sort(key=lambda scenario: scenario.id)

        scenarios = self._all_scenarios if \
            worker_ind is None or n is None else\
            get_portion(self._all_scenarios, n, worker_ind)
        for s in scenarios:
            s.enabled = True

    def _create_actions_collection(self):
        action_lists = (s.actions for s in self._all_scenarios)
        actions = (a for a in itertools.chain(*action_lists))
        return {a.id: a for a in actions}

    def log_enabled_scenarios(self):
        scenarios = [s for s in self._all_scenarios if s.enabled]
        if scenarios:
            LOG.info("Scenarios:\n%s", sorted([s.id for s in scenarios]))
