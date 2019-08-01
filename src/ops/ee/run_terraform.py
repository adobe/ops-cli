# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from config_generator import ConfigProcessor

from ops import Executor
import logging
import os
import six
import yaml

logger = logging.getLogger(__name__)


class CompositionSorter(object):
    def __init__(self, name="terraform", composition_order=None):
        if composition_order is None:
            self.load_static_configs(name)
        else:
            self.composition_order = composition_order

    def load_static_configs(self, name):
        with open(".opsconfig.yaml", 'r') as f:
            content = yaml.load(f)
            self.composition_order = content["compositions_order"][name]

    def get_sorted_compositions(self, compositions, reverse=False):
        result = filter(lambda x: x in compositions, self.composition_order)
        return tuple(reversed(result)) if reverse else result


class CompositionRunner:

    def __init__(self, runner_name="terraform"):
        self.composition_sorter = CompositionSorter(runner_name)
        self.generator = ConfigProcessor()

    def run(self, path, reverse=False):
        all_compositions = self.discover_all_compositions(path)
        compositions = self.get_sorted_compositions(all_compositions, reverse)
        if len(compositions) == 0:
            logger.warn("Skipping runner %s because no compositions were detected for it in %s.", self, path)
        self.do_run(path, compositions)

    def do_run(self, path, compositions):
        pass

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

    def get_sorted_compositions(self, all_compositions, reverse=False):
        return self.composition_sorter.get_sorted_compositions(all_compositions, reverse)

    def get_config_path_for_composition(self, path_prefix, composition):
        return path_prefix if "composition=" in path_prefix else "{}/composition={}".format(path_prefix, composition)


class TerraformRunner(CompositionRunner, object):

    def __init__(self, composition_path, terraform_command, terraform_args):
        super(TerraformRunner, self).__init__("terraform")
        self.composition_path = composition_path
        self.terraform_command = terraform_command
        self.terraform_args = terraform_args
        self.aws_profile = None

    def do_run(self, path, compositions):
        if not self.await_confirmation(compositions):
            return

        for composition in compositions:
            conf_path = self.get_config_path_for_composition(path, composition)
            self.generate_terraform_configs(conf_path, composition)

            for command in self.get_terraform_commands(composition):
                self.run_sh(command)

    def await_confirmation(self, compositions):
        if "-auto-approve" in self.terraform_args:
            return True
        while True:
            answer = six.moves.input("""
Run 'terraform {}' for the following compositions {}?
Only 'yes' will be accepted to approve.
Enter a value: """.format(self.terraform_command, compositions))
            return answer == "yes"

    def generate_terraform_configs(self, path, composition):
        self.generate_provider_config(path, composition)
        self.generate_variables_config(path, composition)

    def generate_provider_config(self, path, composition):
        output_file = self.composition_path + "compositions/terraform/{}/provider.tf.json".format(composition)
        logger.info('Generating terraform config %s', output_file)
        data = self.generator.process(path=path,
                                      filters=["provider", "terraform"],
                                      output_format="json",
                                      output_file=output_file,
                                      skip_interpolation_validation=True,
                                      print_data=True)
        self.aws_profile = data['provider']['aws']['profile']

    def generate_variables_config(self, path, composition):
        output_file = self.composition_path + "compositions/terraform/{}/variables.tfvars.json".format(composition)
        logger.info('Generating terraform config %s', output_file)
        self.generator.process(path=path,
                               exclude_keys=["helm", "provider"],
                               enclosing_key="config",
                               output_format="json",
                               output_file=output_file,

                               # skip validation, since some interpolations might not be able to be resolved
                               # at this point (eg. {{outputs.*}}, which reads from a terraform state file
                               # that might not yet be created)
                               skip_interpolation_validation=True,
                               print_data=True)

    def get_terraform_commands(self, composition):
        commands = []
        commands.append("rm -rf .terraform")

        aws_profile = "AWS_PROFILE={} ".format(self.aws_profile) if self.aws_profile else ""
        commands.append("{}terraform init {}compositions/terraform/{}".format(aws_profile, self.composition_path, composition))

        cmd = ' '.join([self.terraform_command] + self.terraform_args)
        commands.append('{0}terraform {1} '
                        '-var-file="{2}compositions/terraform/{3}/variables.tfvars.json" {2}compositions/terraform/{3}'
                        .format(aws_profile, cmd, self.composition_path, composition))

        return commands
