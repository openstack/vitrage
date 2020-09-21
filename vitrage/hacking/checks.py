# Copyright 2017 - Nokia
# Copyright (c) 2014 OpenStack Foundation.
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

import re

from hacking import core

mutable_default_args = re.compile(r"^\s*def .+\((.+={\}|.+=\[\])")

asse_trueinst_re = re.compile(
    r"(.)*assertTrue\(isinstance\((\w|\.|\'|\"|\[|\])+, "
    r"(\w|\.|\'|\"|\[|\])+\)\)")
asse_equal_type_re = re.compile(
    r"(.)*assertEqual\(type\((\w|\.|\'|\"|\[|\])+\), "
    r"(\w|\.|\'|\"|\[|\])+\)")
asse_equal_end_with_none_re = re.compile(
    r"(.)*assertEqual\((\w|\.|\'|\"|\[|\])+, None\)")
asse_equal_start_with_none_re = re.compile(
    r"(.)*assertEqual\(None, (\w|\.|\'|\"|\[|\])+\)")
unicode_func_re = re.compile(r"(\s|\W|^)unicode\(")

_all_log_levels = {'debug', 'error', 'info', 'warning',
                   'critical', 'exception'}
# Since _Lx have been removed, we just need to check _()
translated_logs = re.compile(
    r"(.)*LOG\.(%(level)s)\(\s*_\(" % {'level': '|'.join(_all_log_levels)})

dict_constructor_with_list_copy_re = re.compile(r".*\bdict\((\[)?([(\[])")


@core.flake8ext
def assert_true_instance(logical_line):
    """Check for assertTrue(isinstance(a, b)) sentences

    V316
    """
    if asse_trueinst_re.match(logical_line):
        yield (0, "V316: assertTrue(isinstance(a, b)) sentences not allowed")


@core.flake8ext
def assert_equal_type(logical_line):
    """Check for assertEqual(type(A), B) sentences

    V317
    """
    if asse_equal_type_re.match(logical_line):
        yield (0, "V317: assertEqual(type(A), B) sentences not allowed")


@core.flake8ext
def no_translate_logs(logical_line):
    """Check for use of LOG.*(_(

    V319
    """
    if translated_logs.match(logical_line):
        yield (0, "V319: Don't translate logs")


@core.flake8ext
def check_no_contextlib_nested(logical_line):
    msg = ("V321: contextlib.nested is deprecated since Python 2.7. See "
           "https://docs.python.org/2/library/contextlib.html#contextlib."
           "nested for more information.")
    if ("with contextlib.nested(" in logical_line or
            "with nested(" in logical_line):
        yield(0, msg)


@core.flake8ext
def dict_constructor_with_list_copy(logical_line):
    msg = ("V322: Must use a dict comprehension instead of a dict constructor "
           "with a sequence of key-value pairs.")
    if dict_constructor_with_list_copy_re.match(logical_line):
        yield (0, msg)


@core.flake8ext
def check_python3_xrange(logical_line):
    if re.search(r"\bxrange\s*\(", logical_line):
        yield(0, "V323: Do not use xrange. Use range, or six.moves.range for "
                 "large loops.")


@core.flake8ext
def check_python3_no_iteritems(logical_line):
    msg = ("V324: Use six.iteritems() or dict.items() instead of "
           "dict.iteritems().")
    if re.search(r".*\.iteritems\(\)", logical_line):
        yield(0, msg)


@core.flake8ext
def check_python3_no_iterkeys(logical_line):
    msg = ("V325: Use six.iterkeys() or dict.keys() instead of "
           "dict.iterkeys().")
    if re.search(r".*\.iterkeys\(\)", logical_line):
        yield(0, msg)


@core.flake8ext
def check_python3_no_itervalues(logical_line):
    msg = ("V326: Use six.itervalues() or dict.values instead of "
           "dict.itervalues().")
    if re.search(r".*\.itervalues\(\)", logical_line):
        yield(0, msg)


@core.flake8ext
def no_mutable_default_args(logical_line):
    msg = "V327: Method's default argument shouldn't be mutable!"
    if mutable_default_args.match(logical_line):
        yield (0, msg)


@core.flake8ext
def no_log_warn(logical_line):
    """Disallow 'LOG.warn('

    V328
    """
    if logical_line.startswith('LOG.warn('):
        yield(0, 'V328: Use LOG.warning() rather than LOG.warn()')


@core.flake8ext
def check_assert_true_false(logical_line):
    """V329 - Don't use assertEqual(True/False, observed)."""
    if re.search(r"assertEqual\(\s*True,[^,]*(,[^,]*)?", logical_line):
        msg = ("V329: Use assertTrue(observed) instead of "
               "assertEqual(True, observed)")
        yield (0, msg)
    if re.search(r"assertEqual\([^,]*,\s*True(,[^,]*)?", logical_line):
        msg = ("V329: Use assertTrue(observed) instead of "
               "assertEqual(True, observed)")
        yield (0, msg)
    if re.search(r"assertEqual\(\s*False,[^,]*(,[^,]*)?", logical_line):
        msg = ("V329: Use assertFalse(observed) instead of "
               "assertEqual(False, observed)")
        yield (0, msg)
    if re.search(r"assertEqual\([^,]*,\s*False(,[^,]*)?", logical_line):
        msg = ("V329: Use assertFalse(observed) instead of "
               "assertEqual(False, observed)")
        yield (0, msg)
