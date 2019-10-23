# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import logging
import getpass
import subprocess

from .parser import SubParserConfig
from . import *

logger = logging.getLogger(__name__)

class SyncParserConfig(SubParserConfig):
    def configure(self, parser):
        parser.add_argument(
            '-l',
            '--user',
            type=str,
            help='Value for remote user that will be used for ssh')
        parser.add_argument('src', type=str, help='Source dir')
        parser.add_argument('dest', type=str, help='Dest dir')
        parser.add_argument(
            'opts',
            default=['-va --progress'],
            nargs='*',
            help='Rsync opts')

    def get_help(self):
        return 'Sync files from/to a cluster'

    def get_name(self):
        return 'sync'

    def get_epilog(self):
        return """
        rsync wrapper for ops inventory conventions

        Example:

        # rsync from remote dcs role
        ops cluster.yml sync 'dcs[0]:/usr/local/demdex/conf' /tmp/configurator-data --user remote_user

        # extra rsync options
        ops cluster.yml sync 'dcs[0]:/usr/local/demdex/conf' /tmp/configurator-data -l remote_user -- --progress
        """


class SyncRunner(object):

    def __init__(self, cluster_config, root_dir,
                 ansible_inventory, inventory_generator, ops_config):
        """
        :type ansible_inventory: ops.inventory.generator.AnsibleInventory
        """

        self.inventory_generator = inventory_generator
        self.ansible_inventory = ansible_inventory
        self.root_dir = root_dir
        self.cluster_config = cluster_config
        self.ops_config = ops_config

    def run(self, args, extra_args):
        logger.info("Found extra_args %s", extra_args)
        inventory_path, ssh_config_path = self.inventory_generator.generate()
        src = PathExpr(args.src)
        dest = PathExpr(args.dest)

        if src.is_remote and dest.is_remote:
            display(
                'Too remote expressions are not allowed',
                stderr=True,
                color='red')
            return

        if src.is_remote:
            remote = src
        else:
            remote = dest

        display(
            "Looking for hosts for pattern '%s'" %
            remote.pattern, stderr=True)

        remote_hosts = []
        hosts = self.ansible_inventory.get_hosts(remote.pattern)
        if not hosts:
            bastion = self.ansible_inventory.get_hosts(
                'bastion')[0].vars.get('ansible_ssh_host')
            remote_hosts.append('{}--{}'.format(bastion, remote.pattern))
        else:
            for host in hosts:
                ssh_host = host.get_vars().get('ansible_ssh_host') or host
                remote_hosts.append(ssh_host)

        for ssh_host in remote_hosts:
            ssh_user = self.cluster_config.get('ssh_user') or self.ops_config.get(
                'ssh.user') or getpass.getuser()
            if remote.remote_user:
                ssh_user = remote.remote_user
            elif args.user:
                ssh_user = args.user

            from_path = src.with_user_and_path(ssh_user, ssh_host)
            to_path = dest.with_user_and_path(ssh_user, ssh_host)

            command = 'rsync {opts} {from_path} {to_path} -e "ssh -F {ssh_config}"'.format(
                opts=" ".join(args.opts),
                from_path=from_path,
                to_path=to_path,
                ssh_config=ssh_config_path

            )

            return dict(command=command)


class PathExpr(object):

    def __init__(self, path):
        self._path = path

    @property
    def is_remote(self):
        return ":" in self._path

    @property
    def path(self):
        return self._path if not self.is_remote else self._path.split(":")[-1]

    @property
    def pattern(self):
        if ':' not in self._path:
            return None

        return self._path if not self.is_remote else self._path.split(":")[
            0].split('@')[-1]

    @property
    def remote_user(self):
        if '@' not in self._path:
            return None

        return self._path.split('@')[0]

    def __str__(self):
        return self._path

    def with_user_and_path(self, ssh_user, ssh_host):
        if self.is_remote:
            user_expr = ''
            if ssh_user:
                user_expr = ssh_user + '@'

            return PathExpr("{user_expr}{host}:{path}".format(
                user_expr=user_expr, host=ssh_host, path=self.path))
        else:
            return self
