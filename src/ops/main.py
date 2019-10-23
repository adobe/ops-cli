# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import sys
import logging
import os

from simpledi import Container, auto, cache, instance, ListInstanceProvider

from .cli.config_generator import ConfigGeneratorParserConfig, ConfigGeneratorRunner
from .cli.config import ClusterConfigGenerator, ClusterConfig
from .cli.inventory import InventoryParserConfig
from .cli.inventory import InventoryRunner
from .cli.parser import RootParser
from .cli.playbook import PlaybookRunner, PlaybookParserConfig
from .cli.run import CommandRunner, CommandParserConfig
from .cli.ssh import SshParserConfig, SshRunner
from .cli.sync import SyncParserConfig, SyncRunner
from .cli.terraform import TerraformParserConfig, TerraformRunner
from .cli.helmfile import HelmfileParserConfig, HelmfileRunner
from .cli.packer import PackerParserConfig, PackerRunner
from .inventory.generator import DirInventoryGenerator, ShellInventoryGenerator, AnsibleInventory, \
    PluginInventoryGenerator, InventoryGenerator, CachedInventoryGenerator
from .inventory.plugin import ec2, legacy_pcs, cns, azr, skms
from .inventory.sshconfig import SshConfigGenerator
from . import OpsException, Executor, validate_ops_version
from .jinja import Template
from .opsconfig import OpsConfig

logger = logging.getLogger(__name__)


def configure_logging(args):
    if args.verbose:
        if args.verbose > 1:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)


class AppContainer(Container):
    def __init__(self, argv=None):
        super(AppContainer, self).__init__()

        self.argv = instance(argv)

        self.configure_parsers()
        self.configure_inventory()

        self.terraform_runner = auto(TerraformRunner)
        self.packer_runner = auto(PackerRunner)
        self.ssh_runner = auto(SshRunner)
        self.play_runner = auto(PlaybookRunner)
        self.run_runner = auto(CommandRunner)
        self.sync_runner = auto(SyncRunner)
        self.helmfile_runner = auto(HelmfileRunner)
        self.config_runner = auto(ConfigGeneratorRunner)

        self.cluster_config = cache(auto(ClusterConfig))
        self.ops_config = cache(auto(OpsConfig))
        self.cluster_config_generator = auto(ClusterConfigGenerator)
        self.ssh_config_generator = auto(SshConfigGenerator)
        self.template = auto(Template)

        # bind the command executor
        self.execute = auto(Executor)

        self.configure()
        self.validate_ops_version()

    def configure_parsers(self):
        self.root_parser = auto(RootParser)

        parsers = ListInstanceProvider()
        parsers.add(auto(InventoryParserConfig))
        parsers.add(auto(TerraformParserConfig))
        parsers.add(auto(PackerParserConfig))
        parsers.add(auto(SshParserConfig))
        parsers.add(auto(PlaybookParserConfig))
        parsers.add(auto(CommandParserConfig))
        parsers.add(auto(SyncParserConfig))
        parsers.add(auto(HelmfileParserConfig))
        parsers.add(auto(ConfigGeneratorParserConfig))
        self.sub_parsers = parsers

    def configure_inventory(self):
        self.inventory_runner = auto(InventoryRunner)
        self.base_inventory_generator = cache(auto(InventoryGenerator))
        self.inventory_generator = cache(auto(CachedInventoryGenerator))
        self.ansible_inventory = cache(auto(AnsibleInventory))

        inventory_generators = ListInstanceProvider()
        inventory_generators.add(auto(DirInventoryGenerator))
        inventory_generators.add(auto(ShellInventoryGenerator))
        inventory_generators.add(auto(PluginInventoryGenerator))

        self.inventory_generators = inventory_generators

        # inventory generator plugins
        inventory_plugins = ListInstanceProvider()
        inventory_plugins.add(instance(ec2))
        inventory_plugins.add(instance(legacy_pcs))
        inventory_plugins.add(instance(cns))
        inventory_plugins.add(instance(azr))
        inventory_plugins.add(instance(skms))
        self.inventory_plugins = inventory_plugins

    def configure(self):
        args, extra_args = self.root_parser.parse_known_args(self.argv)
        configure_logging(args)

        logger.debug('cli args: %s, extra_args: %s', args, extra_args)

        # Bind some very useful dependencies
        self.console_args = cache(instance(args))
        self.console_extra_args = cache(instance(extra_args))
        self.command = lambda c: self.console_args.command
        self.cluster_config_path = cache(
            lambda c: get_cluster_config_path(
                c.root_dir, c.console_args))
        self.root_dir = cache(lambda c: get_root_dir(c.console_args))
        self.cluster_name = lambda c: c.cluster_config['cluster']
        self.package_dir = lambda c: os.path.dirname(__file__)

        # change path to the root_dir
        logger.info('root dir: %s', self.root_dir)
        os.chdir(self.root_dir)

        return args

    def validate_ops_version(self):
        if 'ops.min_version' in self.ops_config:
            validate_ops_version(self.ops_config['ops.min_version'])

    def run(self):
        if 'refresh_cache' in vars(self.console_args):
            os.environ['REFRESH_CACHE'] = str(self.console_args.refresh_cache)
        command_name = '%s_runner' % self.console_args.command
        runner_instance = self.get_instance(command_name)

        return runner_instance.run(self.console_args, self.console_extra_args)


def run(args=None):
    """ App entry point """
    app_container = AppContainer(args)

    output = app_container.run()

    if isinstance(output, int):
        return output
    ret = app_container.execute(output)
    sys.exit(ret)


def get_cluster_config_path(root_dir, console_args):
    """ Return config path + root_dir if path is relative """

    if os.path.isabs(console_args.cluster_config_path):
        return console_args.cluster_config_path
    return os.path.join(root_dir, console_args.cluster_config_path)


def get_root_dir(args):
    """ Either the root_dir option or the current working dir """

    if args.root_dir:
        if not os.path.isdir(os.path.realpath(args.root_dir)):
            raise OpsException(
                "Specified root dir '%s' does not exists" %
                os.path.realpath(
                    args.root_dir))

        return os.path.realpath(args.root_dir)

    return os.path.realpath(os.getcwd())
