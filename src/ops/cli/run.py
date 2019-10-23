# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import logging
from .parser import configure_common_ansible_args, SubParserConfig

logger = logging.getLogger(__name__)

class CommandParserConfig(SubParserConfig):
    def get_epilog(self):
        return '''
    Examples:
        # Last 5 installed packages on each host
        ops qe1.yaml run all 'sudo grep Installed /var/log/yum.log | tail -5'

        # See nodetool status on each cassandra node
        ops qe1.yaml run qe1-cassandra 'nodetool status'

        # Complex limits
        ops qe1.yaml run 'qe1-cassandra,!qe1-cassandra-0' 'nodetool status'

        # Show how to pass other args
        '''

    def configure(self, parser):
        configure_common_ansible_args(parser)
        parser.add_argument(
            'host_pattern',
            type=str,
            help='Limit the run to the following hosts')
        parser.add_argument(
            'shell_command',
            type=str,
            help='Shell command you want to run')
        parser.add_argument(
            'extra_args',
            type=str,
            nargs='*',
            help='Extra ansible arguments')

    def get_help(self):
        return 'Runs a command against hosts in the cluster'

    def get_name(self):
        return 'run'


class CommandRunner(object):

    def __init__(self, ops_config, root_dir, inventory_generator,
                 cluster_config_path, cluster_config):

        self.inventory_generator = inventory_generator
        self.root_dir = root_dir
        self.ops_config = ops_config
        self.cluster_config_path = cluster_config_path
        self.cluster_config = cluster_config

    def run(self, args, extra_args):
        logger.info("Found extra_args %s", extra_args)
        inventory_path, ssh_config_path = self.inventory_generator.generate()
        limit = args.host_pattern

        extra_args = ' '.join(args.extra_args)
        command = """cd {root_dir}
ANSIBLE_SSH_ARGS='-F {ssh_config}' ANSIBLE_CONFIG={ansible_config_path} ansible -i {inventory_path} '{limit}' \\
        -m shell -a '{command}' {extra_args}""".format(
            ssh_config=ssh_config_path,
            ansible_config_path=self.ops_config.ansible_config_path,
            inventory_path=inventory_path,
            command=args.shell_command,
            limit=limit,
            root_dir=self.root_dir,
            extra_args=extra_args
        )

        if args.verbose:
            command += ' -vvv '

        return dict(command=command)
