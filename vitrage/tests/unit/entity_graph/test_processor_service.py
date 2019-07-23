# Copyright 2017 - Nokia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import threading

from vitrage.entity_graph.graph_init import EventsCoordination
from vitrage.tests import base


class EventsCoordinationTest(base.BaseTest):

    @classmethod
    def setUpClass(cls):
        super(EventsCoordinationTest, cls).setUpClass()
        cls.calc_result = 0

    def do_work(self, x):
        if x:
            self.calc_result = self.calc_result * 2
        else:
            self.calc_result = self.calc_result + 1

    def test_queue_coordination(self):
        explain = """
        initially calc_result is 0.
        each high priority call multiplies by *2
        each low priority call adds +1
        so, if all the high calls are performed first, and then all the low,
        the result should be the number of low priority calls.
        0*(2^n) + 1*n
        """
        priority_listener = EventsCoordination(self.do_work)

        def write_high():
            for i in range(10000):
                priority_listener._do_high_priority_work(True)

        def write_low():
            for i in range(10000):
                priority_listener._do_low_priority_work(False)

        self.calc_result = 0
        t1 = threading.Thread(name='high_1', target=write_high)
        t2 = threading.Thread(name='high_2', target=write_high)
        t3 = threading.Thread(name='low_1', target=write_low)
        t4 = threading.Thread(name='low_2', target=write_low)
        self._start_and_join(t1, t2, t3, t4)
        self.assertEqual(20000, self.calc_result, explain)

        self.calc_result = 0
        t1 = threading.Thread(name='high_1', target=write_high)
        t2 = threading.Thread(name='low_1', target=write_low)
        t3 = threading.Thread(name='low_2', target=write_low)
        t4 = threading.Thread(name='high_2', target=write_high)
        self._start_and_join(t1, t2, t3, t4)
        self.assertEqual(20000, self.calc_result, explain)

    def _start_and_join(self, *args):
        for t in args:
            t.start()
        for t in args:
            t.join()
