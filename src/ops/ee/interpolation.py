# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from inject_secrets import SecretInjector


def is_interpolation(input):
    return '{{' in input and '}}' in input


class DictIterator():

    def loop_all_items(self, data, process_func):
        if isinstance(data, basestring):
            return process_func(data)
        if isinstance(data, list):
            items = []
            for item in data:
                items.append(self.loop_all_items(item, process_func))
            return items
        if isinstance(data, dict):
            for key in data:
                value = data[key]
                resolved_value = self.loop_all_items(value, process_func)
                data[key] = resolved_value
        return data


class InterpolationResolver(DictIterator):

    def __init__(self, data, secrets_injector=SecretInjector()):
        self.generated_data = data
        self.secrets_injector = secrets_injector
        self.from_dict_injector = FromDictInjector()

    def resolve_interpolations(self, data):
        return self.loop_all_items(data, self.resolve_interpolation)

    def resolve_interpolation(self, line):
        if not is_interpolation(line):
            return line

        updated_line = self.secrets_injector.inject_secret(line)
        updated_line = self.from_dict_injector.resolve(updated_line, self.generated_data)
        return updated_line


class InterpolationValidator(DictIterator):

    def __init__(self):
        pass

    def check_all_interpolations_resolved(self, data):
        return self.loop_all_items(data, self.validate_value)

    def validate_value(self, value):
        if is_interpolation(value):
            raise Exception("Interpolation could not be resolved {} and strict validation was enabled.".format(value))
        return value


class FromDictInjector():

    def __init__(self):
        self.results = {}

    def resolve(self, line, data):
        """
        :param input: {{env.name}} 
        :param data: (env: name: dev)
        :return: dev
        """

        self.parse_leaves(data, "")
        for key, value in self.results.iteritems():
            line = line.replace("{{" + key + "}}", value)
        return line

    def parse_leaves(self, data, partial_key):
        if isinstance(data, basestring):
            self.results[partial_key] = data
            return
        if isinstance(data, dict):
            for key in data:
                value = data[key]
                new_key = partial_key
                if new_key:
                    new_key += "."
                new_key += key
                self.parse_leaves(value, new_key)
