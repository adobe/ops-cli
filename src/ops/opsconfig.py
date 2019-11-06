# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import os
import yaml
import logging


logger = logging.getLogger(__name__)


def file_tree(config_path, search_fname):
    """ From the current dir returns a list with all the files in the file tree to the root dir """

    parts = os.path.realpath(config_path)

    file_stack = []

    while parts:
        fname = '/'.join((parts, search_fname))
        file_stack.append(fname)
        parts = parts.rpartition('/')[0]

    return file_stack


class OpsConfig(object):
    """
    Parses the all .opsconfig.yaml files that it can find starting from the
    first down the path to the one in the current dir

    For /root/cluster/cluster.yaml:

        /etc/opswrapper/.opsconfig.yaml
        ~/.opsconfig.yaml
        /root/.opsconfig.yaml
        /root/cluster/.opsconfig.yaml
    """

    DEFAULTS = {
        # cache dir
        'cache.dir': '~/.ops/cache',

        # inventory settings
        'inventory.max_age': 600,

        # terraform options
        'terraform.version': 'latest',

        # template settings
        'jinja2.undefined': 'StrictUndefined',  # Undefined, DebugUndefined

        # ssh options
        'ssh.config': None,
        'ssh.default_args': ['-L'],
        'ssh.user': None,

        # ansible options
        'ansible.filter_plugins': 'plugins/filter_plugins',
        'ansible.vars_plugins': 'plugins/vars_plugins',

        # S3 remote state
        'terraform.s3_state': False,

        # Integrate https://github.com/coinbase/terraform-landscape
        'terraform.landscape': False,

        # Remove .terraform folder before each terraform plan, to prevent reuse of installed backends (it can confuse terraform when the cluster backend is
        # not the same for all of them)
        'terraform.remove_local_cache': False,

        # Where the terraform repo will be stored.
        'terraform.root_path': '~/.ops/terraform',

        # From where to fetch the terraform repo if it doesn't exist.
        'terraform.upstream_repo': None,

        # Where the helmfile repo will be stored.
        'helmfile.root_path': '~/.ops/helmfile',

        # From where to fetch the helmfile repo if it doesn't exist.
        'helmfile.upstream_repo': None,
    }

    DEFAULT_PATHS = [
        '/etc/opswrapper/.opsconfig.yaml',
        '~/.opsconfig.yaml'
    ]

    def __init__(self, console_args, package_dir):
        cluster_config_path = console_args.cluster_config_path
        self.config = self.DEFAULTS
        self.package_dir = package_dir

        paths = self.DEFAULT_PATHS[:]
        for fname in reversed(
                file_tree(cluster_config_path, '.opsconfig.yaml')):
            if fname not in paths:
                paths.append(fname)

        parsed_files = []
        logger.debug("parsing %s", paths)

        for config_path in paths:
            config_path = os.path.realpath(os.path.expanduser(config_path))
            if os.path.isfile(config_path):
                logger.info("parsing %s", config_path)
                with open(config_path) as f:
                    config = yaml.safe_load(f.read())
                    if isinstance(config, dict):
                        parsed_files.append(config_path)
                        self.config.update(config)
                    else:
                        logger.error(
                            "cannot parse yaml dict from file: %s", config_path)

        self.parsed_files = parsed_files
        logger.info("final ops config: %s from %s", self.config, parsed_files)

    def get(self, item, default=None):
        return self.config.get(item, default)

    @property
    def ansible_filter_plugins(self):
        # the default filters are in this package
        filters = [self.package_dir + '/ansible/filter_plugins']

        if 'ansible.filter_plugins' in self.config:
            filters.append(self.config['ansible.filter_plugins'])

        return os.path.pathsep.join(filters)

    @property
    def ansible_config_path(self):
        value = self.config.get('ansible.config_path')
        if value:
            return value
        else:
            # the default path is in this package
            return self.package_dir + '/data/ansible/ansible.cfg'

    @property
    def ansible_vars_plugins(self):
        vars = [self.package_dir + '/ansible/vars_plugins']

        if 'ansible.vars_plugins' in self.config:
            vars.append(self.config['ansible.vars_plugins'])

        return os.path.pathsep.join(vars)

    @property
    def ansible_callback_plugins(self):
        vars = [self.package_dir + '/ansible/callback_plugins']

        if 'ansible.callback_plugins' in self.config:
            vars.append(self.config['ansible.callback_plugins'])

        return os.path.pathsep.join(vars)

    @property
    def terraform_config_path(self):
        default_path = self.package_dir + '/data/terraform/terraformrc'
        return self.config.get('terraform.config_path', default_path)

    def __contains__(self, item):
        return item in self.config

    def __getitem__(self, item):
        if item not in self.config:
            raise KeyError("%s not found in %s" % (item, self.parsed_files))

        return self.config[item]

    def all(self):
        return self.config
