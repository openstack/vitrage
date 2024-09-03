# Copyright 2016 - Alcatel-Lucent
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
import itertools

from vitrage.common import utils
from vitrage.tests import base
from vitrage.tests.base import IsEmpty


class UtilsTest(base.BaseTest):

    def _assert_set_equal(self, s1, s2, message):
        self.assertDictEqual(dict.fromkeys(s1, 0),
                             dict.fromkeys(s2, 0),
                             message)

    def test_get_portion(self):
        all_items = list(range(14))
        self._check_portions(all_items, 4)
        self._check_portions(all_items, 3)
        self._check_portions(all_items, 2)
        self._check_portions(all_items, 1)
        self._check_portions(all_items, 51)
        self._check_portions(all_items, 100)

        all_items = [0]
        self._check_portions(all_items, 10)

        all_items = []
        self._check_portions(all_items, 2)

        self._check_portions_bad_params(all_items, 0, 0)
        self._check_portions_bad_params(all_items, -1, 0)
        self._check_portions_bad_params(all_items, 10, 10)

    def _check_portions_bad_params(self, all_items, num, ind):
        exception = None
        try:
            utils.get_portion(all_items, num, ind)
        except Exception as e:
            exception = e
        self.assertIsNotNone(exception, 'get_portion incorrect params')

    def _check_portions(self, all_items, chunks_count):
        chunks = []
        for i in range(chunks_count):
            chunks.append(set(utils.get_portion(all_items, chunks_count, i)))

        union = (a for a in itertools.chain(*chunks))
        self._assert_set_equal(union, set(all_items), 'chunks union differs')
        combinations = itertools.combinations(range(len(chunks)), 2)
        for i, j in combinations:
            self.assertThat(chunks[i].intersection(chunks[j]), IsEmpty(),
                            "Each two chunks should not have "
                            "intersecting items")
        max_size = len(max(chunks, key=lambda x: len(x)))
        min_size = len(min(chunks, key=lambda x: len(x)))
        expected_max_difference = 1 if len(all_items) % len(chunks) else 0
        self.assertEqual(expected_max_difference, max_size - min_size,
                         'chunks sizes should not differ by more than 1')
