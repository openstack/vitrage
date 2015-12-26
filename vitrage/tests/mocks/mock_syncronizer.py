# Copyright 2015 - Alcatel-Lucent
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


"""Methods for generating synchronizer events

For each type of entity, supply a configuration file that specifies a regex
of what can be returned

usage example:
    test_entity_spec_list = [
        {'filename': '../resources/mock_nova_inst_init_snapshot.txt',
         '#instances': 10,
         'name': 'Instance (vm) generator'
         }
    ]
    spec_list = get_mock_generators(test_entity_spec_list)
    events = generate_random_events_list(spec_list)
"""

import random

import mock_generators as mg


default_num=100
#Here you define your default numer 

_NUM_EVENTS_KEY = '#events'
_GENERATOR_KEY = 'generator'
_INSTANCE_NUM_KEY = '#instances'
_FILENAME_KEY = 'filename'
_NAME_KEY = 'name'


def get_mock_generators(entity_spec_list):
    """Returns generators of synchronizer data.

    Each entry in the list should be of the format:
    {
     _FILENAME_KEY: name of file specifying the data returning in each entry,
     _INSTANCE_NUM_KEY: number of instances to generate for
     _NAME_KEY: generator name (used for logging only)
    }

    :param entity_spec_list: specification of the generators to return.
    :type entity_spec_list: list
    :return: list of generators
    :rtype: list
    """
    generator_spec_list = []
    for entity_spec in entity_spec_list:
        generator = mg.MockEventGenerator(
            entity_spec[_FILENAME_KEY],
            entity_spec[_INSTANCE_NUM_KEY],
            entity_spec[_NAME_KEY]
        )
        generator_spec_list.append({_GENERATOR_KEY: generator})
        if _NUM_EVENTS_KEY in entity_spec.keys():
            generator_spec_list[-1][_NUM_EVENTS_KEY] = \
                entity_spec[_NUM_EVENTS_KEY]
    return generator_spec_list


def generate_random_events_list(generator_spec_list, default_num):
    """Generates random events for the generators given.

     Each element in the list of generators includes a generator and
     number of events to generate for it's entities

     :param generator_spec_list: list of generators
     :type generator_spec_list: list

     :param default_num: default number of events to generate
     :type default_num: list

     :return list of synchronizer events
     :rtype list
    """
    data = []
    for spec in generator_spec_list:
        event_num = spec.get(_NUM_EVENTS_KEY, default_num)
        data += spec[_GENERATOR_KEY].generate_data_stream(event_num)
    random.shuffle(data)
    return data
