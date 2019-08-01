#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import os
from ops.cli.parser import SubParserConfig
from ops.ee.run_compositions import AggregatedCompositionRunner

class EEParserConfig(SubParserConfig):
    def get_name(self):
        return 'ee'

    def get_help(self):
        return 'Wrap common terraform/helmfile tasks with hiera-like configuration support'

    def configure(self, parser):
        parser.add_argument('runner', help='terraform | helmfile', type=str)
        parser.add_argument('subcommand', help='plan | sync | apply | template', type=str)
        parser.add_argument('extra_args', type=str, nargs='*', help='Extra args')
        parser.add_argument('--auto-approve', action='store_true', help='Do not require interactive approval')
        parser.add_argument('--composition-path', type=str, default=None, help='Path to compositions')
        return parser

    def get_epilog(self):
        return '''
        '''


class EERunner(object):
    def __init__(self, root_dir, inventory_generator, ops_config, cluster_config_path, cluster_config):
        self.root_dir = root_dir
        self.inventory_generator = inventory_generator
        self.ops_config = ops_config
        self.cluster_config_path = cluster_config_path
        self.cluster_config = cluster_config

    def run(self, args):
        args.path = self.cluster_config_path
        reverse = args.subcommand == "destroy"
        args.composition_path = "" if args.composition_path is None else os.path.join(args.composition_path, '')

        compositions_order = self.cluster_config.ops_config.config["compositions_order"]
        runner = AggregatedCompositionRunner(args, compositions_order)
        runner.run(args.path, reverse)
