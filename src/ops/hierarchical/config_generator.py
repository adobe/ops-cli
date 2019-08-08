#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import os
from collections import OrderedDict
import pathlib2
from deepmerge import Merger
import yaml
import json
from interpolation import InterpolationResolver, InterpolationValidator
from remote_state import S3TerraformRemoteStateRetriever
from ops.cli import display


class ConfigGenerator(object):
    """
    this class is used to create a config generator object which will be used to generate cluster definition files
    from the hierarchy of directories. The class implements methods that performs deep merging on dicts so the end result
    will contain merged data on each layer.
    """

    def __init__(self, cwd, path):
        self.cwd = cwd
        self.path = path
        self.hierarchy = self.generate_hierarchy()
        self.generated_data = OrderedDict()
        self.interpolation_validator = InterpolationValidator()

    @staticmethod
    def yaml_dumper():
        try:
            from yaml import CLoader as Loader, CDumper as Dumper
        except ImportError:
            from yaml import Loader, Dumper
        from yaml.representer import SafeRepresenter
        _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

        def dict_representer(dumper, data):
            return dumper.represent_dict(data.iteritems())

        def dict_constructor(loader, node):
            return OrderedDict(loader.construct_pairs(node))

        Dumper.add_representer(OrderedDict, dict_representer)
        Loader.add_constructor(_mapping_tag, dict_constructor)

        Dumper.add_representer(str,
                               SafeRepresenter.represent_str)

        Dumper.add_representer(unicode,
                               SafeRepresenter.represent_unicode)
        return Dumper

    @staticmethod
    def get_yaml_from_path(working_directory, path):
        yaml_files = []
        for yaml_file in os.listdir(path):
            if yaml_file.endswith(".yaml"):
                yaml_files.append(os.path.join(working_directory, yaml_file))
        return sorted(yaml_files)

    @staticmethod
    def yaml_get_content(yaml_file):
        with open(yaml_file, 'r') as f:
            content = yaml.load(f)
        return content if content else {}

    @staticmethod
    def merge_value(reference, new_value):
        merger = Merger([(list, ["append"]), (dict, ["merge"])], ["override"], ["override"])
        if isinstance(new_value, (list, set, dict)):
            new_reference = merger.merge(reference, new_value)
        else:
            raise TypeError("Cannot handle merge_value of type {}".format(type(new_value)))
        return new_reference

    @staticmethod
    def merge_yamls(values, yaml_content):
        for key, value in yaml_content.iteritems():
            if key in values and not isinstance(value, basestring):
                values[key] = ConfigGenerator.merge_value(values[key], value)
            else:
                values[key] = value

    def generate_hierarchy(self):
        """
        the method will go through the hierarchy of directories and create an ordered list of directories to be used
        when merging data at each layer
        :return: returns a list of directories in a priority order (from less specific to more specific)
        """
        hierarchy = []
        full_path = pathlib2.Path(self.path)
        for path in full_path.parts:
            os.chdir(path)
            new_path = os.path.relpath(os.getcwd(), self.cwd)
            hierarchy.append(self.get_yaml_from_path(new_path, os.getcwd()))
        os.chdir(self.cwd)
        return hierarchy

    def process_hierarchy(self):
        merged_values = OrderedDict()
        for yaml_files in self.hierarchy:
            for yaml_file in yaml_files:
                yaml_content = self.yaml_get_content(yaml_file)
                self.merge_yamls(merged_values, yaml_content)
        self.generated_data = merged_values

    def get_values_from_dir_path(self):
        values = {}
        full_path = pathlib2.Path(self.path)
        for path in full_path.parts[1:]:
            split_value = path.split('=')
            values[split_value[0]] = split_value[1]
        return values

    def output_yaml_data(self, data):
        return yaml.dump(data, Dumper=ConfigGenerator.yaml_dumper(), default_flow_style=False)

    def yaml_to_json(self, yaml_data):
        return json.dumps(yaml.load(yaml_data), indent=4)

    def output_data(self, data, format):
        yaml_data = self.output_yaml_data(data)
        if "yaml" in format:
            return yaml_data
        elif "json" in format:
            return self.yaml_to_json(yaml_data)
        raise Exception("Unknown output format: {}".format(format))

    def add_enclosing_key(self, key):
        return {key: self.generated_data}

    def filter_data(self, keys):
        self.generated_data = {key: self.generated_data[key] for key in keys if key in self.generated_data}

    def exclude_keys(self, keys):
        for key in keys:
            if key in self.generated_data:
                del self.generated_data[key]

    def add_dynamic_data(self):
        remote_state_retriever = S3TerraformRemoteStateRetriever()
        if "remote_states" in self.generated_data:
            state_files = self.generated_data["remote_states"]
            remote_states = remote_state_retriever.get_dynamic_data(state_files)
            self.merge_value(self.generated_data, remote_states)

    def resolve_interpolations(self):
        resolver = InterpolationResolver(self.generated_data)
        self.generated_data = resolver.resolve_interpolations(self.generated_data)

    def validate_interpolations(self):
        self.interpolation_validator.check_all_interpolations_resolved(self.generated_data)


class ConfigProcessor(object):
    def process(self, cwd=None, path=None, filters=(), exclude_keys=(), enclosing_key=None, output_format=yaml, print_data=False,
                output_file=None, skip_interpolations=False, skip_interpolation_validation=False, display_command=True):

        if display_command:
            command = self.get_sh_command(path, filters, enclosing_key, output_format, print_data, output_file,
                                          skip_interpolations, skip_interpolation_validation)
            display(command, color='yellow')

        if skip_interpolations:
            skip_interpolation_validation = True

        if cwd is None:
            cwd = os.getcwd()

        generator = ConfigGenerator(cwd, path)
        generator.generate_hierarchy()
        generator.process_hierarchy()

        if not skip_interpolations:
            generator.resolve_interpolations()
            generator.add_dynamic_data()
            generator.resolve_interpolations()

        if len(filters) > 0:
            generator.filter_data(filters)

        if len(exclude_keys) > 0:
            generator.exclude_keys(exclude_keys)

        if not skip_interpolation_validation:
            generator.validate_interpolations()

        data = generator.add_enclosing_key(enclosing_key) if enclosing_key else generator.generated_data

        formatted_data = generator.output_data(data, output_format)

        if print_data:
            print(formatted_data)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(formatted_data)

        return data

    @staticmethod
    def get_sh_command(path, filters, enclosing_key, output_format, print_data,
                       output_file, skip_interpolations, skip_interpolation_validation):
        command = "ops {} config --format {}".format(path, output_format)
        for filter in filters:
            command += " --filter {}".format(filter)
        if enclosing_key:
            command += " --enclosing-key {}".format(enclosing_key)
        if output_file:
            command += " --output-file {}".format(output_file)
        if print_data:
            command += " --print-data"
        if skip_interpolations:
            command += " --skip-interpolation-resolving"
        if skip_interpolation_validation:
            command += " --skip-interpolation-validation"

        return command
