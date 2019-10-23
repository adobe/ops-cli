# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import logging
from himl.main import ConfigRunner
from ops.cli.parser import SubParserConfig

logger = logging.getLogger(__name__)

class ConfigGeneratorParserConfig(SubParserConfig):
    def get_name(self):
        return 'config'

    def get_help(self):
        return 'Generate configurations based on a hierarchical structure, with templating support'

    def configure(self, parser):
        return ConfigRunner().get_parser(parser)

    def get_epilog(self):
        return '''
        Examples:
        # Generate config
        ops data/account=ee-dev/env=dev/region=va6/project=ee/cluster=experiments/composition=helmfiles config --format json --print-data
        '''


class ConfigGeneratorRunner(object):
    def __init__(self, cluster_config_path):
        self.cluster_config_path = cluster_config_path

    def run(self, args, extra_args):
        logger.info("Found extra_args %s", extra_args)
        logging.basicConfig(level=logging.INFO)
        args.path = self.cluster_config_path
        if args.output_file is None:
            args.print_data = True

        ConfigRunner().do_run(args)
