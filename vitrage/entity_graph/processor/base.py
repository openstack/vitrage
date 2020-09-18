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

import abc


class ProcessorBase(object, metaclass=abc.ABCMeta):

    def __init__(self):
        pass

    @abc.abstractmethod
    def process_event(self, event):
        pass

    @abc.abstractmethod
    def create_entity(self, new_vertex, neighbors):
        pass

    @abc.abstractmethod
    def update_entity(self, updated_vertex, neighbors):
        pass

    @abc.abstractmethod
    def delete_entity(self, deleted_vertex, neighbors):
        pass
