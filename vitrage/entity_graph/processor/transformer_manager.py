# Copyright 2015 - Alcatel-Lucent
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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from vitrage.common.constants import DatasourceProperties as DSProps
from vitrage.common.exception import VitrageTransformerError
from vitrage.datasources.consistency import CONSISTENCY_DATASOURCE
from vitrage.datasources.consistency.transformer import ConsistencyTransformer
from vitrage.evaluator.actions.evaluator_event_transformer import \
    EvaluatorEventTransformer
from vitrage.evaluator.actions.evaluator_event_transformer \
    import VITRAGE_DATASOURCE
from vitrage.utils import opt_exists

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
ENTITIES = 'entities'


class TransformerManager(object):

    def __init__(self):
        self.transformers = self.register_transformer_classes()

    @staticmethod
    def register_transformer_classes():

        transformers = {}
        for datasource_type in CONF.datasources.types:
            try:
                transformers[datasource_type] = importutils.import_object(
                    CONF[datasource_type].transformer,
                    transformers)
                if opt_exists(CONF[datasource_type], ENTITIES):
                    for entity in CONF[datasource_type].entities:
                        transformers[entity] = importutils.import_object(
                            CONF[datasource_type].transformer,
                            transformers)

            except Exception:
                LOG.exception('Failed to register transformer %s.',
                              datasource_type)

        transformers[VITRAGE_DATASOURCE] = importutils.import_object(
            "%s.%s" % (EvaluatorEventTransformer.__module__,
                       EvaluatorEventTransformer.__name__), transformers)

        transformers[CONSISTENCY_DATASOURCE] = importutils.import_object(
            "%s.%s" % (ConsistencyTransformer.__module__,
                       ConsistencyTransformer.__name__), transformers)

        return transformers

    def get_transformer(self, key):
        try:
            transformer = self.transformers[key]
        except KeyError:
            raise VitrageTransformerError(
                'Could not get transformer instance for %s' % key)

        return transformer

    def transform(self, entity_event):
        entity_type = self.get_entity_type(entity_event)
        return self.get_transformer(entity_type).transform(entity_event)

    def get_enrich_query(self, entity_event):
        entity_type = self.get_entity_type(entity_event)
        return self.get_transformer(entity_type).get_enrich_query(entity_event)

    @staticmethod
    def get_entity_type(entity_event):
        try:
            return entity_event[DSProps.ENTITY_TYPE]
        except KeyError:
            raise VitrageTransformerError(
                'Entity Event must contains entity_type field.')
