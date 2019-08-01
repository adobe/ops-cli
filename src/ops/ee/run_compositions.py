#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

from run_terraform import CompositionRunner
from run_terraform import TerraformRunner
from run_helmfile import HelmfileRunner
import logging

logger = logging.getLogger(__name__)


class AggregatedCompositionRunner(CompositionRunner):

    def __init__(self, opts):
        self.runners = self.generate_runners(opts)

    def generate_runners(self, opts):
        if opts.runner == "terraform":
            return [self.get_terraform_runner(opts)]
        if opts.runner == "helmfile":
            return [self.get_helmfile_runner(opts)]
        if opts.runner == "all":
            return [self.get_terraform_runner(opts),
                    self.get_helmfile_runner(opts)]
        raise Exception("Unknown command '{}'. Supported values are: terraform | helmfile | all".format(opts.runner))

    def get_terraform_runner(self, opts):
        terraform_args = opts.extra_args[:]
        if opts.auto_approve:
            terraform_args.append("-auto-approve")
        subcommand = self.get_terraform_command(opts.subcommand)
        return TerraformRunner(opts.composition_path, subcommand, terraform_args)

    def get_helmfile_runner(self, opts):
        subcommand = self.get_helmfile_command(opts.subcommand)
        return HelmfileRunner(opts.composition_path, subcommand, opts.extra_args)

    def get_terraform_command(self, subcommand):
        if subcommand in ("plan", "apply", "destroy", "template", "validate"):
            return subcommand
        raise Exception("Supported terraform subcommands are plan | apply | destroy | template | validate. You selected {}".format(subcommand))

    def get_helmfile_command(self, subcommand):
        if subcommand in ("sync", "template", "destroy", "apply"):
            return subcommand
        elif subcommand == "plan":
            return "diff"
        else:
            raise Exception("Supported helmfile subcommands are plan | apply | sync | template | destroy. You selected {}".format(subcommand))

    def run(self, path, reverse=False):
        runners = tuple(reversed(self.runners)) if reverse else self.runners
        for runner in runners:
            runner.run(path)
