# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from himl.config_generator import ConfigProcessor

from ops import Executor, display
import logging
import os

logger = logging.getLogger(__name__)


class CompositionConfigGenerator:

    def __init__(self, composition_order):
        self.composition_sorter = CompositionSorter(composition_order)
        self.config_generator = HierarchicalConfigGenerator()

    def get_sorted_compositions(self, path, reverse=False):
        all_compositions = self.discover_all_compositions(path)
        compositions = self.sort_compositions(all_compositions, reverse)
        return compositions

    def discover_all_compositions(self, path):
        path_params = dict(self.split_path(x) for x in path.split('/'))

        composition = path_params.get("composition", None)
        if composition:
            return [composition]

        return self.get_compositions_in_path(path)

    def get_compositions_in_path(self, path):
        compositions = []
        subpaths = os.listdir(path)
        for subpath in subpaths:
            if "composition=" in subpath:
                composition = self.split_path(subpath)[1]
                compositions.append(composition)
        return compositions

    def run_sh(self, command, cwd=None, exit_on_error=True):
        args = {"command": command}
        execute = Executor()
        exit_code = execute(args, cwd=cwd)
        if exit_code != 0:
            logger.error("Command finished with non zero exit code.")
            if exit_on_error:
                exit(exit_code)

    def split_path(self, value, separator='='):
        if separator in value:
            return value.split(separator)
        return [value, ""]

    def sort_compositions(self, all_compositions, reverse=False):
        return self.composition_sorter.get_sorted_compositions(
            all_compositions, reverse)

    def get_config_path_for_composition(self, path_prefix, composition):
        prefix = os.path.join(path_prefix, '')
        return path_prefix if "composition=" in path_prefix else "{}composition={}".format(
            prefix, composition)

    def get_terraform_path_for_composition(self, path_prefix, composition):
        prefix = os.path.join(path_prefix, '')
        return path_prefix if composition in path_prefix else "{}{}/".format(
            prefix, composition)


class TerraformConfigGenerator(CompositionConfigGenerator, object):

    def __init__(self, composition_order, excluded_config_keys):
        super(TerraformConfigGenerator, self).__init__(composition_order)
        self.excluded_config_keys = excluded_config_keys

    def generate_files(self, config_path, composition_path, composition):
        config_path = self.get_config_path_for_composition(
            config_path, composition)
        composition_path = self.get_terraform_path_for_composition(
            composition_path, composition)
        self.generate_provider_config(config_path, composition_path)
        self.generate_variables_config(
            composition, config_path, composition_path)

    def generate_provider_config(self, config_path, composition_path):
        output_file = "{}provider.tf.json".format(composition_path)
        logger.info('Generating terraform config %s', output_file)
        self.config_generator.generate_config(config_path=config_path,
                                              filters=[
                                                  "provider", "terraform"],
                                              output_format="json",
                                              output_file=output_file,
                                              print_data=True)

    def generate_variables_config(self, composition, config_path, composition_path):
        output_file = os.path.expanduser(
            os.path.join(composition_path, "variables.tfvars.json")
        )
        logger.info('Generating terraform config %s', output_file)

        excluded_keys = ["helm", "provider"]
        if composition in self.excluded_config_keys:
            excluded_keys += self.excluded_config_keys[composition]

        self.config_generator.generate_config(config_path=config_path,
                                              exclude_keys=excluded_keys,
                                              enclosing_key="config",
                                              output_format="json",
                                              output_file=output_file,
                                              print_data=True)


class CompositionSorter(object):
    def __init__(self, composition_order):
        self.composition_order = composition_order

    def get_sorted_compositions(self, compositions, reverse=False):
        result = list(
            filter(
                lambda x: x in compositions,
                self.composition_order))
        return tuple(reversed(result)) if reverse else result


class HierarchicalConfigGenerator(object):
    def __init__(self):
        self.config_processor = ConfigProcessor()

    def generate_config(self, config_path, filters=(), exclude_keys=(), enclosing_key=None, output_format="yaml",
                        print_data=False, output_file=None):
        cmd = self.get_sh_command(config_path, filters, exclude_keys, enclosing_key, output_format, print_data,
                                  output_file)
        display(cmd, color="yellow")
        return self.config_processor.process(path=config_path,
                                             filters=filters,
                                             exclude_keys=exclude_keys,
                                             enclosing_key=enclosing_key,
                                             output_format=output_format,
                                             output_file=os.path.expanduser(output_file),
                                             print_data=print_data)

    @staticmethod
    def get_sh_command(config_path, filters=(), exclude_keys=(), enclosing_key=None, output_format="yaml",
                       print_data=False, output_file=None):
        command = "ops {} config --format {}".format(
            config_path, output_format)
        for filter in filters:
            command += " --filter {}".format(filter)
        for exclude in exclude_keys:
            command += " --exclude {}".format(exclude)
        if enclosing_key:
            command += " --enclosing-key {}".format(enclosing_key)
        if output_file:
            command += " --output-file {}".format(output_file)
        if print_data:
            command += " --print-data"

        return command
