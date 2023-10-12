# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from subprocess import call

from . import display
from .parser import SubParserConfig
from .parser import configure_common_arguments
from ansible.inventory.host import Host
from ops.inventory.sshconfig import SshConfigGenerator

from . import err
import sys
import getpass
import re
import os
import logging

logger = logging.getLogger(__name__)
IP_HOST_REG_EX = re.compile(r'^((\d+)\.(\d+)\.(\d+)\.(\d+):)?(\d+)$')


class SshParserConfig(SubParserConfig):
    def get_name(self):
        return 'ssh'

    def configure(self, parser):
        configure_common_arguments(parser)
        parser.add_argument(
            'role',
            type=str,
            help='Server role to ssh to. Eg: dcs')
        parser.add_argument('-l', '--user', type=str, help='SSH User')
        parser.add_argument(
            '--ssh-config',
            type=str,
            help='Ssh config file name in the ./ansible dir')
        parser.add_argument(
            '--index',
            type=int,
            default=1,
            help='Index of the server from the group')
        parser.add_argument(
            'ssh_opts',
            default=[],
            nargs='*',
            help='Manual ssh options')
        parser.add_argument(
            '--tunnel',
            action="store_true",
            help="Use SSH tunnel, must pass --local and --remote")
        parser.add_argument('--ipaddress', action="store_true")
        parser.add_argument(
            '--local',
            type=str,
            help="local [host-ip:]port for ssh proxy or ssh tunnel")
        parser.add_argument(
            '--remote',
            type=int,
            help="remote port for ssh tunnel")
        parser.add_argument(
            '--proxy',
            action="store_true",
            help="Use SSH proxy, must pass --local or when using scb, either --auto_scb_port or "
                 "no extra option which will use scb.proxy_port from cluster_config")
        parser.add_argument(
            '--nossh',
            action="store_true",
            help="Port tunnel a machine that does not have SSH. "
                 "Implies --ipaddress, and --tunnel; requires --local and --remote"
                )
        parser.add_argument(
            '--keygen',
            action='store_true',
            help='Create a ssh keys pair to use with this infrastructure')
        parser.add_argument(
            '--noscb',
            action='store_false',
            dest='use_scb',
            help='Disable use of Shell Control Box (SCB) even if it is '
                 'enabled in the cluster config')
        parser.add_argument(
            '--auto_scb_port',
            action='store_true',
            help='When using Shell Control Box (SCB) and creating a proxy,'
                 'a random port is generated, which will be used in the ssh config '
                 'for all playbook, run and sync operations')

    def get_help(self):
        return 'SSH or create an SSH tunnel to a server in the cluster'

    def get_epilog(self):
        return '''
    Examples:
        # SSH using current username as remote username
        ops clusters/qe1.yaml ssh nagios

        # SSH using a different username
        ops clusters/qe1.yaml ssh nagios -l ec2-user

        # SSH to the second nagios instance
        ops clusters/qe1.yaml ssh nagios --index 2

        # SSH to a specific hostname, instead of the tagged role
        ops clusters/qe1.yaml ssh full-hostname-here-1

        # Create an SSH tunnel to Nagios forwarding the remote port 80 to local port 8080
        ops clusters/qe1.yaml ssh --tunnel --remote 80 --local 8080 nagios

        # Create an SSH tunnel to a host where the service is NOT listening on `localhost`
        ops clusters/qe1.yaml ssh --tunnel --remote 80 --local 8080 nagios --ipaddress

        # Create an SSH tunnel to a host with an open port which does NOT have SSH itself (Windows)
        # Note that the connection will be made from the Bastion host
        ops clusters/qe1.yaml ssh --tunnel --local 3389 --remote 3389 --nossh windowshost
        ops clusters/qe1.yaml ssh --tunnel --local 127.0.0.0.1:3389 --remote 3389 --nossh windowshost

        # Create a proxy to a remote server that listens on a local port
        ops clusters/qe1.yaml ssh --proxy --local 8080 bastion
        ops clusters/qe1.yaml ssh --proxy --local 0.0.0.0:8080 bastion

        # In case Shell Control Box (SCB) is configured and enabled on the cluster a proxy which
        # will be used by all ops play, run and sync operations, can be created either using
        # either the port configured the cluster config file or an auto generated port.
        # In this case --local param must not be used
        # Example for using the port configured in the cluster config
        ops clusters/qe1.yaml ssh bastion --proxy
        # Example for using the auto generated port
        ops clusters/qe1.yaml ssh bastion --proxy --auto_scb_port

        # Disable use of Shell Control Box (SCB) even it is enabled in the cluster config
        ops clusters/qe1.yaml ssh bastion --noscb
        '''


class SshRunner(object):

    def __init__(self, cluster_config_path, cluster_config,
                 ansible_inventory, ops_config, cluster_name, root_dir):
        """
        :type ansible_inventory: ops.inventory.generator.AnsibleInventory
        """

        self.root_dir = root_dir
        self.cluster_name = cluster_name
        self.ops_config = ops_config
        self.cluster_config = cluster_config
        self.ansible_inventory = ansible_inventory

    def run(self, args, extra_args):
        logger.info("Found extra_args %s", extra_args)
        if args.keygen:
            if self.cluster_config.has_ssh_keys:
                err('Cluster already has ssh keys, refusing to overwrite')
                sys.exit(2)
            else:
                pub_key_file = self.cluster_config.cluster_ssh_pubkey_file
                prv_key_file = self.cluster_config.cluster_ssh_prvkey_file
                display(
                    'Trying to generate ssh keys in:\n{} and \n{}'.format(
                        pub_key_file, prv_key_file))
                if os.path.isfile(
                        pub_key_file) or os.path.isfile(prv_key_file):
                    err('Although we do not have a complete keyset, one of the files exists and we refuse to overwrite\n')
                    sys.exit(2)
                else:
                    # generate ssh keypair. The passphrase will be the name of
                    # the cluster
                    cmd = "ssh-keygen -t rsa -b 4096 -N {} -f {}".format(
                        self.cluster_name, prv_key_file).split(' ')
                    print(cmd)
                    call(cmd)
            return

        if args.local and not IP_HOST_REG_EX.match(args.local):
            err('The --local parameter must be in the form of host-ip:port or port')
            sys.exit(2)

        if args.tunnel or args.nossh:
            if args.local is None or args.remote is None:
                err('When using --tunnel or --nossh both the --local and --remote parameters are required')
                sys.exit(2)

        scb_settings = self.cluster_config.get('scb', {})
        scb_enabled = scb_settings.get('enabled') and args.use_scb
        scb_host = scb_settings.get('host') or self.ops_config.get('scb.host')
        scb_proxy_port = scb_settings.get('proxy_port')

        if scb_enabled and not scb_host:
            err('When scb is enabled scb_host is required!')
            sys.exit(2)

        if args.proxy:
            if args.local is None and (args.auto_scb_port is False and not scb_proxy_port):
                err('When using --proxy the --local parameter is required if not using '
                    '--auto_scb_port and scb.proxy_port is not configured in the cluster config')
                sys.exit(2)

        group = "%s,&%s" % (self.cluster_name, args.role)

        args.index = args.index - 1
        if args.index < 0:
            args.index = 0

        hosts = self.ansible_inventory.get_hosts(group)
        if len(hosts) <= args.index:
            group = args.role
            hosts = self.ansible_inventory.get_hosts(group)
            if not hosts:
                display(
                    "No host found in inventory, using provided name %s" %
                    (args.role), color="purple", stderr=True)

        display("Expression %s matched hosts (max 10): " % group, stderr=True)
        host_names = [host.name for host in hosts]
        for name in host_names[:10]:
            display(name, color='blue')

        host = None
        if host_names:
            if args.index < len(host_names):
                host = self.ansible_inventory.get_host(host_names[args.index])
            else:
                display(
                    "Index out of bounds for %s" %
                    (group), color="red", stderr=True)
                return
        if host:
            ssh_host = host.vars.get('ansible_ssh_host') or host.name
        else:
            # no host found in inventory, use the role provided
            bastion = self.ansible_inventory.get_hosts(
                'bastion')[0].vars.get('ansible_ssh_host')
            host = Host(name=args.role)
            ssh_host = f'{bastion}--{host.name}'
        ssh_user = self.cluster_config.get('ssh_user') or self.ops_config.get(
            'ssh.user') or getpass.getuser()
        if args.user:
            ssh_user = args.user
        if ssh_user and '-l' not in args.ssh_opts:
            args.ssh_opts.extend(['-l', ssh_user])

        if args.nossh:
            args.tunnel = True
            args.ipaddress = True
            ssh_host = self.ansible_inventory.get_hosts(
                'bastion')[0].vars.get('ansible_ssh_host')

        # if args.tunnel or args.proxy:
        #     ssh_config = args.ssh_config or 'ssh.tunnel.config'
        # else:
        #     ssh_config = args.ssh_config or self.ansible_inventory.get_ssh_config()
        ssh_config = args.ssh_config or self.ops_config.get(
            'ssh.config') or self.ansible_inventory.get_ssh_config()

        scb_ssh_host = None
        if scb_enabled:
            # scb->bastion->host vs scb->bastion
            scb_delimiter = "--" if "--" in ssh_host else "@"
            scb_ssh_host = f"{ssh_host}{scb_delimiter}{scb_host}"

        if args.tunnel:
            if args.ipaddress:
                host_ip = host.vars.get('private_ip_address')
            else:
                host_ip = 'localhost'
            if scb_enabled:
                command = f"ssh -F {ssh_config} {ssh_user}@{scb_ssh_host} " \
                          f"-4 -T -L {args.local}:{host_ip}:{args.remote:d}"
            else:
                command = f"ssh -F {ssh_config} {ssh_host} " \
                          f"-4 -N -L {args.local}:{host_ip}:{args.remote:d}"
        else:
            if scb_enabled:
                command = f"ssh -F {ssh_config} {ssh_user}@{scb_ssh_host}"
            else:
                command = f"ssh -F {ssh_config} {ssh_host}"

        if args.proxy:
            if scb_enabled:
                proxy_port = args.local or SshConfigGenerator.generate_ssh_scb_proxy_port(
                    self.ansible_inventory.generated_path.removesuffix("/inventory"),
                    args.auto_scb_port,
                    scb_proxy_port
                )
                command = f"ssh -F {ssh_config} {ssh_user}@{scb_ssh_host} " \
                          f"-4 -T -D {proxy_port} -o 'ExitOnForwardFailure yes'"
            else:
                command = f"ssh -F {ssh_config} {ssh_host} " \
                          f"-4 -N -D {args.local} -f -o 'ExitOnForwardFailure yes'"

        if args.ssh_opts:
            command = f"{command} {' '.join(args.ssh_opts)}"

        # Check if optional sshpass is available and print info message
        sshpass_path = os.path.expanduser("~/bin/sshpass")
        if (os.path.isfile(sshpass_path) and os.access(sshpass_path, os.X_OK)):
            display("Using sshpass passwordless wrapper at %s" %
                    (sshpass_path), color="green", stderr=True)
        else:
            display("sshpass passwordless wrapper NOT available in %s" %
                    (sshpass_path), color="purple", stderr=True)

        display(
            "SSH-ing to %s[%d] => %s" %
            (args.role,
             args.index,
             host.name),
            color="green",
            stderr=True)

        return dict(command=command)
