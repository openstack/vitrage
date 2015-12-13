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

__author__ = 'erosensw'

"""
Mock event generator.

Generator will generate events for a specific entity type, as defined
by a configuration file. A single generator can generate events for
multiple instances of the same entity type.

"""

from os.path import curdir
from os import walk
import random

from entity_model import CommonEntityModel as cem


def _get_filename_path(filename):
    base_dir = None
    for i in walk("../../%s" % curdir):
        if i[0].find('resources') != -1 and filename in i[2]:
            base_dir = i[0]
            break
    if base_dir is None:
        raise IOError("No file {0} in resources folder".format(filename))
    else:
        return '{0}/{1}'.format(base_dir, filename)


class MockEventGenerator(object):
    """Represents a single generator.

    A generator can generate events for several instances of the same type
    """

    def __init__(self, filename, instance_num, generator_name='generator'):
        self.config_file = _get_filename_path(filename)
        self.static_params = {}
        self.dynamic_params = {}
        self.instance_num = instance_num
        self.models = []
        self.name = generator_name

        self.load_entry_config_file()
        self.prepare_instance_models()

    def load_entry_config_file(self):
        """Load the configuration file.

        From the configuration file, we get the key-value specification of each
        field in the data entry
        """

        params_dict = {'s': self.static_params, 'd': self.dynamic_params}
        try:
            for line in open(self.config_file):
                line_params = line.split()
                param_type = line_params[1].lower()
                params_dict[param_type][line_params[0]] = line_params[2]
        except KeyError as ke:
            print("Syntax error: {0}".format(ke.message))

    def prepare_instance_models(self):
        """Create the models for all the instances """

        for i in range(self.instance_num):
            model = cem(static_params=self.static_params,
                        dynamic_params=self.dynamic_params)
            model.generate_all_params()
            self.models.append(model)

    def generate_data_stream(self, event_num=100):
        """Generates a list of events.

        :param event_num: number of events to generate
        :type event_num: int
        :return: list of generated events
        :rtype: list
        """

        data_stream = []
        for _ in xrange(event_num):
            model = self.models[random.randint(0, self.instance_num - 1)]
            model.generate_dynamic_params()
            data_stream.append(model.params)
        return data_stream
 
