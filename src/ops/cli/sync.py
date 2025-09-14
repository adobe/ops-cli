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
from ops.inventory.sshconfig import SshConfigGenerator

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
        parser.add_argument('--noscb', action='store_false', dest='use_scb',
                            help='Disable use of Shell Control Box (SCB) '
                                 'even if it is enabled in the cluster config')
        parser.add_argument(
            '--teleport',
            action='store_false',
            dest='use_teleport',
            help='Use Teleport for SSH')
        parser.add_argument(
            'opts',
            nargs='*',
            help='Sync opts')

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

        # extra sync option for Teleport (recursive download, quiet, port)
        ops cluster.yml sync 'dcs[0]:/usr/local/demdex/conf' /tmp/configurator-data -- --recursive/port/quiet
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
        
        src = PathExpr(args.src)
        dest = PathExpr(args.dest)
        remote = self.get_remote(dest, src)

        if src.is_remote and dest.is_remote:
            display(
                'Two remote expressions are not allowed',
                stderr=True,
                color='red')
            return

        display(
            "Looking for hosts for pattern '%s'" %
            remote.pattern, stderr=True)

        if self.is_teleport_enabled(args):
            command = self.execute_teleport_scp(args, src, dest)
        else:
            ssh_user = self.cluster_config.get('ssh_user') or self.ops_config.get('ssh.user') or getpass.getuser()
            if remote.remote_user:
                ssh_user = remote.remote_user
            elif args.user:
                ssh_user = args.user
            ssh_host = self.populate_remote_hosts(remote)[0]
            command = self.execute_rsync_scp(args, src, dest, ssh_user, ssh_host, self.get_ssh_config_path(args))

        return dict(command=command)

    def populate_remote_hosts(self, remote):
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
        return remote_hosts

    def get_remote(self, dest, src):
        if src.is_remote:
            remote = src
        else:
            remote = dest
        return remote

    def get_ssh_config_path(self, args):
        ssh_config_generator = SshConfigGenerator(self.ops_config.package_dir)
        _, ssh_config_paths = self.inventory_generator.generate()
        return ssh_config_generator.get_ssh_config_path(self.cluster_config,
                                                ssh_config_paths,
                                                
                                                args)

    def execute_teleport_scp(self, args, src, dest):
        return 'tsh scp {opts} {from_path} {to_path}'.format(
                    from_path=src,
                    to_path=dest,
                    opts=" ".join(args.opts)
                )

    def execute_rsync_scp(self, args, src, dest, ssh_user, ssh_host, ssh_config_path):
        from_path = src.with_user_and_path(ssh_user, ssh_host)
        to_path = dest.with_user_and_path(ssh_user, ssh_host)
        return 'rsync {opts} {from_path} {to_path} -e "ssh -F {ssh_config}"'.format(
                    opts=" ".join(args.opts),
                    from_path=from_path,
                    to_path=to_path,
                    ssh_config=ssh_config_path
                )
                

    def is_teleport_enabled(self, args):
         return True if self.cluster_config.get('teleport', {}).get('enabled') and args.use_teleport else False

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
