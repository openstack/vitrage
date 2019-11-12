# Copyright 2015 - Alcatel-Lucent
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

import logging
import os

from oslo_config import cfg
from oslo_config import fixture as config_fixture
from oslo_utils import timeutils
# noinspection PyPackageRequirements
from oslotest import base
import sys

from testtools import matchers
from testtools.matchers import HasLength

from vitrage.common import config

CONF = cfg.CONF
IsEmpty = lambda: HasLength(0)


class BaseTest(base.BaseTestCase):
    """Test case base class for all unit tests."""

    def conf_reregister_opts(self, opts, group=None):
        self.conf.reset()
        if group in self.conf:
            for opt in opts:
                self.conf.unregister_opt(opt, group=group)
        self.conf.register_opts(opts, group=group)

        def unregister_opts():
            self.conf.reset()
            for opt in opts:
                self.conf.unregister_opt(opt, group=group)

        self.addCleanup(unregister_opts)

    def setUp(self):
        super(BaseTest, self).setUp()
        self.cfg_fixture = self.useFixture(
            config_fixture.Config(CONF))
        config.parse_config([])
        logging.disable(logging.CRITICAL)
        self.conf = self.cfg_fixture.conf

    def config(self, **kw):
        self.cfg_fixture.config(**kw)

    def assert_list_equal(self, l1, l2, message=None):
        if tuple(sys.version_info)[0:2] < (2, 7):
            # for python 2.6 compatibility
            self.assertEqual(l1, l2, message)
        else:
            super(BaseTest, self).assertListEqual(l1, l2, message)

    def assert_dict_equal(self, d1, d2, message=None):
        if tuple(sys.version_info)[0:2] < (2, 7):
            # for python 2.6 compatibility
            self.assertEqual(d1, d2)
        else:
            super(BaseTest, self).assertDictEqual(d1, d2, message)

    def assert_timestamp_equal(self, first, second, msg=None):
        """Checks that two timestamps are equals.

        This relies on assertAlmostEqual to avoid rounding problem, and only
        checks up the first microsecond values.

        """
        return self.assertAlmostEqual(timeutils.delta_seconds(first, second),
                                      0.0,
                                      places=5, msg=msg)

    def assert_is_empty(self, obj):
        try:
            if len(obj) != 0:
                self.fail("%s is not empty" % type(obj))
        except (TypeError, AttributeError):
            self.fail("%s doesn't have length" % type(obj))

    def assert_is_not_empty(self, obj):
        try:
            if len(obj) == 0:
                self.fail("%s is empty" % type(obj))
        except (TypeError, AttributeError):
            self.fail("%s doesn't have length" % type(obj))

    def assert_graph_equal(self, g1, g2):
        """Checks that two graphs are equals.

        This relies on assert_dict_equal when comparing the nodes and the
        edges of each graph.
        """
        g1_nodes = g1._g.nodes
        g1_edges = g1._g.adj
        g2_nodes = g2._g.nodes
        g2_edges = g2._g.adj
        self.assertEqual(g1.num_vertices(), g2.num_vertices(),
                         "Two graphs have different amount of nodes")
        self.assertEqual(g1.num_edges(), g2.num_edges(),
                         "Two graphs have different amount of edges")
        for n_id in g1_nodes:
            self.assert_dict_equal(g1_nodes.get(n_id),
                                   g2_nodes.get(n_id),
                                   "Nodes of each graph are not equal")

        for e_source_id in g1_edges:
            self.assert_dict_equal(dict(g1_edges.get(e_source_id)),
                                   dict(g2_edges.get(e_source_id)),
                                   "Edges of each graph are not equal")

    def assert_starts_with(self, expected_prefix, observed_str, msg=None):
        self.assertThat(observed_str,
                        matchers.StartsWith(expected_prefix), msg)

    @staticmethod
    def path_get(project_file=None):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            '..',
                                            '..',
                                            )
                               )
        if project_file:
            return os.path.join(root, project_file)
        else:
            return root
