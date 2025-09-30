# Copyright 2025 - Adria Cloud Services
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


from vitrage.common.exception import VitrageError
from vitrage.graph import query
from vitrage.tests import base


class QueryTest(base.BaseTest):

    def test_simple_query_equal(self):
        q = {'==': {'vitrage_category': 'ALARM'}}
        match = query.create_predicate(q)
        self.assertTrue(match({'vitrage_category': 'ALARM'}))
        self.assertFalse(match({'vitrage_category': 'RESOURCE'}))

    def test_simple_query_not_equal(self):
        q = {'!=': {'vitrage_category': 'ALARM'}}
        match = query.create_predicate(q)
        self.assertFalse(match({'vitrage_category': 'ALARM'}))
        self.assertTrue(match({'vitrage_category': 'RESOURCE'}))

    def test_simple_query_greater_than(self):
        q = {'>': {'vitrage_value': 100}}
        match = query.create_predicate(q)
        self.assertTrue(match({'vitrage_value': 101}))
        self.assertFalse(match({'vitrage_value': 100}))
        self.assertFalse(match({'vitrage_value': 99}))

    def test_simple_query_greater_or_equal(self):
        q = {'>=': {'vitrage_value': 100}}
        match = query.create_predicate(q)
        self.assertTrue(match({'vitrage_value': 101}))
        self.assertTrue(match({'vitrage_value': 100}))
        self.assertFalse(match({'vitrage_value': 99}))

    def test_simple_query_less_than(self):
        q = {'<': {'vitrage_value': 100}}
        match = query.create_predicate(q)
        self.assertFalse(match({'vitrage_value': 101}))
        self.assertFalse(match({'vitrage_value': 100}))
        self.assertTrue(match({'vitrage_value': 99}))

    def test_simple_query_less_or_equal(self):
        q = {'<=': {'vitrage_value': 100}}
        match = query.create_predicate(q)
        self.assertFalse(match({'vitrage_value': 101}))
        self.assertTrue(match({'vitrage_value': 100}))
        self.assertTrue(match({'vitrage_value': 99}))

    def test_query_with_non_existent_key(self):
        q = {'==': {'non_existent_key': 'some_value'}}
        match = query.create_predicate(q)
        self.assertFalse(match({'vitrage_category': 'ALARM'}))

    def test_implicit_and_in_comparison(self):
        q = {'==': {'category': 'ALARM', 'type': 'nova.instance'}}
        match = query.create_predicate(q)
        self.assertTrue(match({'category': 'ALARM', 'type': 'nova.instance'}))
        self.assertFalse(match({'category': 'ALARM', 'type': 'cinder.volume'}))
        self.assertFalse(match(
            {'category': 'RESOURCE', 'type': 'nova.instance'}
        ))

    def test_and_query(self):
        q = {
            'and': [
                {'==': {'vitrage_category': 'ALARM'}},
                {'>': {'vitrage_value': 100}}
            ]
        }
        match = query.create_predicate(q)
        self.assertTrue(
            match({'vitrage_category': 'ALARM', 'vitrage_value': 101}))
        self.assertFalse(
            match({'vitrage_category': 'ALARM', 'vitrage_value': 100}))
        self.assertFalse(
            match({'vitrage_category': 'RESOURCE', 'vitrage_value': 101}))

    def test_or_query(self):
        q = {
            'or': [
                {'==': {'vitrage_category': 'ALARM'}},
                {'>': {'vitrage_value': 100}}
            ]
        }
        match = query.create_predicate(q)
        self.assertTrue(
            match({'vitrage_category': 'ALARM', 'vitrage_value': 99}))
        self.assertTrue(
            match({'vitrage_category': 'RESOURCE', 'vitrage_value': 101}))
        self.assertFalse(
            match({'vitrage_category': 'RESOURCE', 'vitrage_value': 100}))

    def test_complex_nested_query(self):
        """Test case from the function's docstring """
        q = {
            'and': [
                {'==': {'CATEGORY': 'ALARM'}},
                {'or': [
                    {'>': {'TIME': 150}},
                    {'==': {'VITRAGE_IS_DELETED': True}}
                ]}
            ]
        }
        match = query.create_predicate(q)

        # ALARM and TIME > 150 -> True
        item1 = {'CATEGORY': 'ALARM', 'TIME': 200, 'VITRAGE_IS_DELETED': False}
        self.assertTrue(match(item1))

        # ALARM and VITRAGE_IS_DELETED -> True
        item2 = {'CATEGORY': 'ALARM', 'TIME': 100, 'VITRAGE_IS_DELETED': True}
        self.assertTrue(match(item2))

        # Not ALARM -> False
        item3 = {
            'CATEGORY': 'RESOURCE', 'TIME': 200, 'VITRAGE_IS_DELETED': True
        }
        self.assertFalse(match(item3))

        # ALARM but neither of the 'or' conditions met -> False
        item4 = {'CATEGORY': 'ALARM', 'TIME': 150, 'VITRAGE_IS_DELETED': False}
        self.assertFalse(match(item4))

    def test_empty_query_raises_error(self):
        self.assertRaises(VitrageError, query.create_predicate, {})

    def test_invalid_operator_raises_error(self):
        q = {'~=': {'key': 'value'}}
        self.assertRaises(VitrageError, query.create_predicate, q)

    def test_invalid_query_structure_raises_error(self):
        q = {'and': {'key': 'value'}}  # 'and' expects a list
        self.assertRaises(VitrageError, query.create_predicate, q)

    def test_empty_list_for_and_operator(self):
        # An empty 'and' should return False
        q = {'and': []}
        match = query.create_predicate(q)
        self.assertFalse(match({'any': 'item'}))

    def test_empty_list_for_or_operator(self):
        # any([]) is False, so an empty 'or' should never match
        q = {'or': []}
        match = query.create_predicate(q)
        self.assertFalse(match({'any': 'item'}))

    def test_empty_dict_for_comparison_operator(self):
        # A comparison with no conditions should be considered False
        q = {'==': {}}
        match = query.create_predicate(q)
        self.assertFalse(match({'any': 'item'}))
