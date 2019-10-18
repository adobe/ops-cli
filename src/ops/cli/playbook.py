# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from .parser import SubParserConfig
from .parser import configure_common_ansible_args, configure_common_arguments
import getpass
import logging

logger = logging.getLogger(__name__)

class PlaybookParserConfig(SubParserConfig):
    def get_name(self):
        return 'play'

    def get_epilog(self):
        return '''
    Examples:
        # Run an ansible playbook
        ops clusters/qe1.yaml play ansible/plays/cluster/configure.yaml

        # Limit the run of a playbook to a subgroup
        ops clusters/qe1.yaml play ansible/plays/cluster/configure.yaml -- --limit dcs

        # Overwrite or set a variable
        ops clusters/qe1.yaml play ansible/plays/cluster/configure.yaml -- -e city=paris

        # Filter with tags
        ops clusters/qe1.yaml play ansible/plays/cluster/configure.yaml -- -t common

        # Run a playbook and overwrite the default user
        ops clusters/qe1.yaml play ansible/plays/cluster/configure.yaml -- -u ec2-user
        '''

    def configure(self, parser):
        configure_common_arguments(parser)
        configure_common_ansible_args(parser)
        parser.add_argument(
            'playbook_path',
            type=str,
            help='The playbook path')
        parser.add_argument(
            'ansible_args',
            type=str,
            nargs='*',
            help='Extra ansible args')

    def get_help(self):
        return 'Run an Ansible playbook'


class PlaybookRunner(object):
    def __init__(self, ops_config, root_dir, inventory_generator,
                 cluster_config_path, cluster_config):
        """
        :type inventory_generator: ops.inventory.generator.InventoryGenerator
        """

        self.inventory_generator = inventory_generator
        self.root_dir = root_dir
        self.ops_config = ops_config
        self.cluster_config_path = cluster_config_path
        self.cluster_config = cluster_config

    def run(self, args, extra_args):
        logger.info("Found extra_args %s", extra_args)
        inventory_path, ssh_config_path = self.inventory_generator.generate()

        ssh_config = "ANSIBLE_SSH_ARGS='-F %s'" % ssh_config_path
        ansible_config = "ANSIBLE_CONFIG=%s" % self.ops_config.ansible_config_path

        # default user: read from cluster then from ops config then local user
        default_user = self.cluster_config.get('ssh_user') \
            or self.ops_config.get('ssh.user') \
            or getpass.getuser()

        if not has_arg(args.ansible_args, 'u', 'user') and default_user:
            args.ansible_args.extend(['-u', default_user])

        if not has_arg(args.ansible_args, 'i', 'inventory-file'):
            args.ansible_args.extend(['-i', inventory_path])

        extra_vars = dict(cluster=self.cluster_config['cluster'])
        if "environment" in self.cluster_config.get(
                "terraform", {}).get("vars", {}):
            extra_vars["environment"] = self.cluster_config["terraform"]["vars"]["environment"]
        extra_vars_args = ' '.join([' -e %s=%s ' % (k, v)
                                    for k, v in extra_vars.items()])

        play_args = ' '.join(args.ansible_args)
        play_args = extra_vars_args + play_args

        command = "cd {root_dir}; " \
                  "OPS_CLUSTER_CONFIG={cluster_config} " \
                  "ANSIBLE_FILTER_PLUGINS={filter_plugins} " \
                  "ANSIBLE_VARS_PLUGINS={vars_plugins} " \
                  "ANSIBLE_CALLBACK_PLUGINS={callback_plugins} " \
                  "{ansible_config} {ssh_config} ansible-playbook {play} {args}".format(
                      root_dir=self.root_dir,
                      cluster_config=self.cluster_config_path,
                      ansible_config=ansible_config,
                      ssh_config=ssh_config,
                      play=args.playbook_path,
                      args=play_args,
                      filter_plugins=self.ops_config.ansible_filter_plugins,
                      vars_plugins=self.ops_config.ansible_vars_plugins,
                      callback_plugins=self.ops_config.ansible_callback_plugins
                  )

        return dict(command=command)


def has_arg(container, *args):
    for arg in args:
        if len(arg) == 1:
            arg = '-' + arg
        else:
            arg = '--' + arg

        if arg in container:
            return True

    return False
