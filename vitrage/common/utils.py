# -*- encoding: utf-8 -*-
# Copyright 2015 - Alcatel-Lucent
# Copyright © 2014-2015 eNovance
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
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
import base64
from collections import defaultdict
import copy
import hashlib
import itertools
import pickle
import random
import threading
import time
import zlib

from oslo_config import cfg
from oslo_log import log

import cProfile

LOG = log.getLogger(__name__)


def recursive_keypairs(d, separator='.'):
    # taken from ceilometer and gnocchi
    for name, value in sorted(d.items()):
        if isinstance(value, dict):
            for subname, subvalue in recursive_keypairs(value, separator):
                yield ('%s%s%s' % (name, separator, subname), subvalue)
        else:
            yield name, value


def opt_exists(conf_parent, opt):
    try:
        return conf_parent[opt]
    except cfg.NoSuchOptError:
        return False


def do_cprofile(func):
    def profiled_func(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            profile.print_stats('cumulative')
    return profiled_func


def get_portion(lst, num_of_portions, portion_index):
    """Split a list into n slices and return the i'th slice

    :rtype: list
    """
    # First shuffle the items to create an even distribution
    # Use the same random seed to always get the same shuffle
    if num_of_portions < 1 or portion_index < 0 or \
            portion_index >= num_of_portions:
        raise Exception('Cannot get_portion %s %s',
                        num_of_portions,
                        portion_index)

    list_copy = copy.copy(lst)
    random.Random(0.5).shuffle(list_copy)

    portions = defaultdict(list)
    portion_indexes = range(num_of_portions)
    g = itertools.cycle(portion_indexes)
    for curr_item in list_copy:
        curr_portion = next(g)
        portions[curr_portion].append(curr_item)
    return portions[portion_index]


def spawn(target, *args, **kwargs):
    t = threading.Thread(target=target, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
    return t


def md5(obj):
    if isinstance(obj, tuple):
        obj = str([str(o) for o in obj])

    if isinstance(obj, str):
        return hashlib.md5(obj.encode('utf-8')).hexdigest()
    raise Exception('Unknown object for md5 %s' % obj)


def fmt(docstr):
    """Format a docstring for use as documentation in sample config."""
    # Replace newlines with spaces, as docstrings contain literal newlines that
    # should not be rendered into the sample configuration file (instead, line
    # wrappings should be applied automatically).
    docstr = docstr.replace('\n', ' ')

    # Because it's common for docstrings to begin and end with a newline, there
    # is now whitespace at the beginning and end of the documentation as a side
    # effect of replacing newlines with spaces.
    docstr = docstr.strip()

    return docstr


def timed_method(log_results=False, warn_above_sec=-1):
    def _decorator(function):
        def wrapper(*args, **kwargs):
            t1 = time.time()
            result = function(*args, **kwargs)
            t2 = time.time()
            if 0 < warn_above_sec < t2 - t1:
                LOG.warning(
                    'Function %s runtime crossed limit %s seconds.',
                    function.__name__, t2 - t1)
            elif log_results:
                LOG.info('Function %s timed %s', function.__name__, t2 - t1)
            return result
        return wrapper
    return _decorator


def compress_obj(obj, level=9):
    str_data = pickle.dumps(obj)
    data = base64.b64encode(zlib.compress(str_data, level))
    return data


def decompress_obj(blob):
    decoded_blob = base64.standard_b64decode(blob)
    str_data = zlib.decompress(decoded_blob)
    obj = pickle.loads(str_data)
    del decoded_blob
    del str_data
    return obj


def to_int(i):
    return int(i) if i is not None else i
