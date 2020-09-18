# Copyright 2016 - Nokia
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

import abc


class HandlerBase(object, metaclass=abc.ABCMeta):

    def __init__(self):
        pass

    @abc.abstractmethod
    def undefined_property(self):
        pass

    @abc.abstractmethod
    def value_properties(self):
        pass

    @abc.abstractmethod
    def set_aggregated_value(self, new_vertex, aggregated_value):
        pass

    @abc.abstractmethod
    def set_operational_value(self, new_vertex, operational_value):
        pass

    @abc.abstractmethod
    def default_values(self):
        pass

    @abc.abstractmethod
    def get_value_class_instance(self):
        pass
