# Copyright 2016 - Nokia
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

from vitrage.graph.utils import check_property_with_regex


def check_filter(data, attr_filter, *args):
    """Check attr_filter against data

    :param data: a dictionary of field_name: value
    :param attr_filter: a dictionary of either
    field_name : value (mandatory)
    field_name : list of values - data[field_name] must match ANY of the values
    :param args: list of filter keys to ignore  (if exist)
    :rtype: bool
    """
    if not attr_filter:
        return True
    for key, content in attr_filter.items():
        if key in args:
            continue
        if not isinstance(content, list):
            content = [content]
        if data.get(key) not in content:
            # import of .regex constant removed, as it was circular
            if key.lower().endswith('.regex'):
                new_key = key[:-len('.regex')]
                if not check_property_with_regex(new_key, content[0],
                                                 data):
                    return False
            else:
                return False
    return True
