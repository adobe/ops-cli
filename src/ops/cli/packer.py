# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import logging
from ops.cli.parser import SubParserConfig
from . import aws

logger = logging.getLogger(__name__)

class PackerParserConfig(SubParserConfig):
    def get_name(self):
        return 'packer'

    def get_help(self):
        return 'Wrap common packer tasks and inject variables from a cluster file'

    def configure(self, parser):
        parser.add_argument('subcommand', help='build | validate', type=str)
        return parser

    def get_epilog(self):
        return '''
    Examples:
        # Validate a packer file
        ops clusters/centos7.yaml packer validate

        # Build a packer file
        ops clusters/centos7.yaml packer build
        '''


class PackerRunner(object):
    def __init__(self, root_dir, cluster_config):
        self.cluster_config = cluster_config
        self.root_dir = root_dir

    def run(self, args, extra_args):
        logger.info("Found extra_args %s", extra_args)
        config_all = self.cluster_config.all()

        packer_variables = config_all['packer']['variables']

        if config_all['packer']['clouds'] is not None:
            if 'aws' in config_all['packer']['clouds']:
                profile_name = config_all['packer']['clouds']['aws']['boto_profile']
                packer_variables['aws_access_key'] = aws.access_key(
                    profile_name)
                packer_variables['aws_secret_key'] = aws.secret_key(
                    profile_name)
            else:
                # add other cloud logic here
                pass

        variables = ''
        for key, value in packer_variables.items():
            variables += " -var '%s=%s' " % (key, value)

        if args.subcommand == 'build':
            command = 'packer build %s %s' % (
                variables, config_all['packer']['template'])

        if args.subcommand == 'validate':
            command = 'packer validate %s %s' % (
                variables, config_all['packer']['template'])

        return dict(
            command=command
        )
