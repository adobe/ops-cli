#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import os
import logging
from ops.hierarchical.config_generator import ConfigProcessor
from ops.cli.parser import SubParserConfig


class ConfigGeneratorParserConfig(SubParserConfig):
    def get_name(self):
        return 'config'

    def get_help(self):
        return 'Wrap common terraform tasks with full templated configuration support'

    def configure(self, parser):
        parser.add_argument('--cwd', dest='cwd', type=str, default="",
                            help='the working directory')
        parser.add_argument('--print-data', action='store_true',
                            help='print generated data on screen')
        parser.add_argument('--enclosing-key', dest='enclosing_key', type=str,
                            help='enclosing key of the generated data')
        parser.add_argument('--output-file', dest='output_file', type=str,
                            help='output file location')
        parser.add_argument('--format', dest='output_format', type=str, default="yaml",
                            help='output file format')
        parser.add_argument('--filter', dest='filter', action='append',
                            help='keep these keys from the generated data')
        parser.add_argument('--exclude', dest='exclude', action='append',
                            help='exclude these keys from generated data')
        parser.add_argument('--skip-interpolation-validation', action='store_true',
                            help='will not throw an error if interpolations can not be resolved')
        parser.add_argument('--skip-interpolation-resolving', action='store_true',
                            help='do not perform any AWS calls to resolve interpolations')
        return parser

    def get_epilog(self):
        return '''
        
        '''


class ConfigGeneratorRunner(object):
    def __init__(self, root_dir, inventory_generator, ops_config, cluster_config_path):
        self.root_dir = root_dir
        self.inventory_generator = inventory_generator
        self.ops_config = ops_config
        self.cluster_config_path = cluster_config_path

    def run(self, args):
        logging.basicConfig(level=logging.INFO)
        args.path = self.cluster_config_path
        if args.output_file is None:
            args.print_data = True
        cwd = args.cwd if args.cwd else os.getcwd()
        filters = args.filter if args.filter else ()
        excluded_keys = args.exclude if args.exclude else ()

        generator = ConfigProcessor()
        generator.process(cwd, args.path, filters, excluded_keys, args.enclosing_key, args.output_format,
                          args.print_data,
                          args.output_file, args.skip_interpolation_resolving, args.skip_interpolation_validation,
                          display_command=False)
