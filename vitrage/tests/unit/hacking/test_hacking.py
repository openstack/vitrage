#    Copyright 2016 - Nokia
#    Copyright 2014 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from testtools import matchers

from vitrage.hacking import checks
from vitrage.tests import base
from vitrage.tests.base import IsEmpty


class HackingTestCase(base.BaseTest):
    def test_assert_true_instance(self):
        self.assertThat(list(checks.assert_true_instance(
            "self.assertTrue(isinstance(e, "
            "exception.BuildAbortException))")), matchers.HasLength(1))

        self.assertThat(list(checks.assert_true_instance("self.assertTrue("
                                                         ")")), IsEmpty())

    def test_assert_equal_type(self):
        self.assertThat(list(checks.assert_equal_type(
            "self.assertEqual(type(als['QuicAssist']), list)")),
            matchers.HasLength(1))

        self.assertThat(list(checks.assert_equal_type("self.assertTrue()")),
                        IsEmpty())

    def test_no_translate_logs(self):
        for log in checks._all_log_levels:
            bad = 'LOG.%s(_("Bad"))' % log
            self.assertThat(list(checks.no_translate_logs(bad)),
                            matchers.HasLength(1))
            # Catch abuses when used with a variable and not a literal
            bad = 'LOG.%s(_(msg))' % log
            self.assertThat(list(checks.no_translate_logs(bad)),
                            matchers.HasLength(1))

    def test_no_contextlib_nested(self):
        self.assertThat(list(checks.check_no_contextlib_nested(
            "with contextlib.nested(")), matchers.HasLength(1))

        self.assertThat(list(checks.check_no_contextlib_nested(
            "with nested(")), matchers.HasLength(1))

        self.assertThat(list(checks.check_no_contextlib_nested(
            "with foo as bar")), IsEmpty())

    def test_dict_constructor_with_list_copy(self):
        self.assertThat(list(checks.dict_constructor_with_list_copy(
            "    dict([(i, connect_info[i])")), matchers.HasLength(1))

        self.assertThat(list(checks.dict_constructor_with_list_copy(
            "    attrs = dict([(k, _from_json(v))")), matchers.HasLength(1))

        self.assertThat(list(checks.dict_constructor_with_list_copy(
            "        type_names = dict((value, key) for key, value in")),
            matchers.HasLength(1))

        self.assertThat(list(checks.dict_constructor_with_list_copy(
            "   dict((value, key) for key, value in")), matchers.HasLength(1))

        self.assertThat(list(checks.dict_constructor_with_list_copy(
            "foo(param=dict((k, v) for k, v in bar.items()))")),
            matchers.HasLength(1))

        self.assertThat(list(checks.dict_constructor_with_list_copy(
            " dict([[i,i] for i in range(3)])")), matchers.HasLength(1))

        self.assertThat(list(checks.dict_constructor_with_list_copy(
            "  dd = dict([i,i] for i in range(3))")), matchers.HasLength(1))

        self.assertThat(list(checks.dict_constructor_with_list_copy(
            "        create_kwargs = dict(snapshot=snapshot,")), IsEmpty())

        self.assertThat(list(checks.dict_constructor_with_list_copy(
            "      self._render_dict(xml, data_el, data.__dict__)")),
            IsEmpty())

    def test_check_python3_xrange(self):
        func = checks.check_python3_xrange
        self.assertThat(list(func('for i in xrange(10)')),
                        matchers.HasLength(1))
        self.assertThat(list(func('for i in range(10)')), IsEmpty())
        self.assertThat(list(func('for i in six.moves.range(10)')), IsEmpty())
        self.assertThat(list(func('testxrange(10)')), IsEmpty())

    def test_dict_iteritems(self):
        self.assertThat(list(checks.check_python3_no_iteritems(
            "obj.iteritems()")), matchers.HasLength(1))

        self.assertThat(list(checks.check_python3_no_iteritems(
            "six.iteritems(obj)")), IsEmpty())

        self.assertThat(list(checks.check_python3_no_iteritems(
            "obj.items()")), IsEmpty())

    def test_dict_iterkeys(self):
        self.assertThat(list(checks.check_python3_no_iterkeys(
            "obj.iterkeys()")), matchers.HasLength(1))

        self.assertThat(list(checks.check_python3_no_iterkeys(
            "six.iterkeys(obj)")), IsEmpty())

        self.assertThat(list(checks.check_python3_no_iterkeys(
            "obj.keys()")), IsEmpty())

    def test_dict_itervalues(self):
        self.assertThat(list(checks.check_python3_no_itervalues(
            "obj.itervalues()")), matchers.HasLength(1))

        self.assertThat(list(checks.check_python3_no_itervalues(
            "six.itervalues(ob)")), IsEmpty())

        self.assertThat(list(checks.check_python3_no_itervalues(
            "obj.values()")), IsEmpty())

    def test_no_mutable_default_args(self):
        self.assertThat(list(checks.no_mutable_default_args(
            " def fake_suds_context(calls={}):")), matchers.HasLength(1))

        self.assertThat(list(checks.no_mutable_default_args(
            "def get_info_from_bdm(virt_type, bdm, mapping=[])")),
            matchers.HasLength(1))

        self.assertThat(list(checks.no_mutable_default_args(
            "defined = []")), IsEmpty())

        self.assertThat(list(checks.no_mutable_default_args(
            "defined, undefined = [], {}")), IsEmpty())

    def test_no_log_warn(self):
        self.assertThat(list(checks.no_log_warn('LOG.warning("bl")')),
                        IsEmpty())
        self.assertThat(list(checks.no_log_warn('LOG.warn("foo")')),
                        matchers.HasLength(1))

    def test_asserttruefalse(self):
        true_fail_code1 = """
               test_bool = True
               self.assertEqual(True, test_bool)
               """
        true_fail_code2 = """
               test_bool = True
               self.assertEqual(test_bool, True)
               """
        true_pass_code = """
               test_bool = True
               self.assertTrue(test_bool)
               """
        false_fail_code1 = """
               test_bool = False
               self.assertEqual(False, test_bool)
               """
        false_fail_code2 = """
               test_bool = False
               self.assertEqual(test_bool, False)
               """
        false_pass_code = """
               test_bool = False
               self.assertFalse(test_bool)
               """
        self.assertThat(list(checks.check_assert_true_false(
            true_fail_code1)), matchers.HasLength(1))
        self.assertThat(list(checks.check_assert_true_false(
            true_fail_code2)), matchers.HasLength(1))
        self.assertThat(list(checks.check_assert_true_false(
            true_pass_code)), IsEmpty())
        self.assertThat(list(checks.check_assert_true_false(
            false_fail_code1)), matchers.HasLength(1))
        self.assertThat(list(checks.check_assert_true_false(
            false_fail_code2)), matchers.HasLength(1))
        self.assertFalse(list(checks.check_assert_true_false(false_pass_code)))
