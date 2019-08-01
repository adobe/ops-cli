# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from run_terraform import CompositionRunner

import logging

logger = logging.getLogger(__name__)


class HelmfileRunner(CompositionRunner, object):

    def __init__(self, composition_path, helmfile_command, helmfile_args):
        super(HelmfileRunner, self).__init__("helmfile")
        self.composition_path = composition_path
        self.helmfile_command = helmfile_command
        self.helmfile_args = helmfile_args

    def do_run(self, path_prefix, compositions):
        composition = compositions[0]
        if composition != "helmfiles":
            raise Exception("Please provide the full path to composition=helmfiles")

        conf_path = self.get_config_path_for_composition(path_prefix, composition)
        self.generate_helmfile_config(conf_path)

        for command in self.get_helmfile_commands():
            self.run_sh(command, cwd=self.composition_path + "compositions/helmfiles")

    def generate_helmfile_config(self, path):
        output_file = self.composition_path + "compositions/helmfiles/hiera-generated.yaml"
        logger.info('Generating helmfiles config %s', output_file)
        self.generator.process(path=path,
                               filters=["helm"],
                               output_format="yaml",
                               output_file=output_file,
                               print_data=True)

    def get_helmfile_commands(self):
        cmd = ' '.join(self.helmfile_args + [self.helmfile_command])
        return ["pwd",
                "helmfile {}".format(cmd)]
