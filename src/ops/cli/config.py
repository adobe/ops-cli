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

from ansible.module_utils.common.collections import ImmutableDict
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar
from ansible.utils.vars import combine_vars
from ansible.vars.manager import VariableManager
from ops.cli import display
from ansible import constants as C
from ansible import context
import logging
from ansible.errors import AnsibleOptionsError
from ansible.module_utils._text import to_text
from ansible.parsing.splitter import parse_kv
from collections.abc import MutableMapping

logger = logging.getLogger(__name__)


def get_cluster_name(cluster_config_path):
    """ Get from path/to/cluster_name.yaml -> cluster_name """

    return cluster_config_path.split(',')[0].split(
        '/')[-1].replace('.yaml', '').replace('.yml', '')


def load_extra_vars(loader):
    """
    Overriding Ansible function using version before slight var loading optimization
    in order to avoid caching issues https://github.com/ansible/ansible/pull/78835/files
    """

    extra_vars = {}
    for extra_vars_opt in context.CLIARGS.get('extra_vars', tuple()):
        data = None
        extra_vars_opt = to_text(extra_vars_opt, errors='surrogate_or_strict')
        if extra_vars_opt is None or not extra_vars_opt:
            continue

        if extra_vars_opt.startswith(u"@"):
            # Argument is a YAML file (JSON is a subset of YAML)
            data = loader.load_from_file(extra_vars_opt[1:])
        elif extra_vars_opt[0] in [u'/', u'.']:
            raise AnsibleOptionsError("Please prepend extra_vars filename '%s' with '@'" % extra_vars_opt)
        elif extra_vars_opt[0] in [u'[', u'{']:
            # Arguments as YAML
            data = loader.load(extra_vars_opt)
        else:
            # Arguments as Key-value
            data = parse_kv(extra_vars_opt)

        if isinstance(data, MutableMapping):
            extra_vars = combine_vars(extra_vars, data)
        else:
            raise AnsibleOptionsError("Invalid extra vars data supplied. '%s' could not be made into a dictionary" % extra_vars_opt)
    return extra_vars


class ClusterConfig(object):
    def __init__(self, cluster_config_generator,
                 ops_config, cluster_config_path):
        """
        :type cluster_config_generator: ClusterConfigGenerator
        """

        self.cluster_config_path = cluster_config_path
        self.cluster_config_generator = cluster_config_generator
        self.ops_config = ops_config
        self.conf = self.cluster_config_generator.get()
        self.load_ssh_keys(cluster_config_path)

    def get(self, item, default=None):
        return self.conf.get(item, default)

    def all(self):
        return self.conf

    def __contains__(self, item):
        return item in self.conf or item in self.ops_config

    def __setitem__(self, key, val):
        self.conf[key] = val

    def __getitem__(self, item):
        if item not in self.conf and item not in self.ops_config:
            msg = "Configuration value %s not found; update your %s" % (
                item, self.cluster_config_path)
            display(msg, color='red', stderr=True)
            return

        if item in self.conf:
            return self.conf[item]

        return self.ops_config[item]

    def load_ssh_keys(self, cluster_config_path):
        cluster_name = get_cluster_name(cluster_config_path)
        self.cluster_ssh_pubkey_file = "{dirn}{s}{cluster}-ssh.key.pub".format(
            s=os.sep, cluster=cluster_name, dirn=os.path.dirname(cluster_config_path))
        self.cluster_ssh_prvkey_file = "{dirn}{s}{cluster}-ssh.key".format(
            s=os.sep, cluster=cluster_name, dirn=os.path.dirname(cluster_config_path))
        self.cluster_ssh_pubkey = None
        self.cluster_ssh_prvkey = None
        try:
            self.cluster_ssh_pubkey = open(self.cluster_ssh_pubkey_file).read()
            self.cluster_ssh_prvkey = open(self.cluster_ssh_prvkey_file).read()
        except Exception as e:
            pass
            # does not matter, if we cannot read them we do not use them

        if self.cluster_ssh_pubkey and self.cluster_ssh_prvkey:
            self.has_ssh_keys = True
            self.conf['has_ssh_keys'] = True
            self.conf['cluster_ssh_pubkey'] = self.cluster_ssh_pubkey
            self.conf['cluster_ssh_prvkey'] = self.cluster_ssh_prvkey
            self.conf['cluster_ssh_pubkey_file'] = self.cluster_ssh_pubkey_file
            self.conf['cluster_ssh_prvkey_file'] = self.cluster_ssh_prvkey_file
        else:
            self.has_ssh_keys = False


class JinjaConfigGenerator(object):
    def __init__(self, console_args, cluster_config_path, template):
        self.cluster_config_path = cluster_config_path
        self.console_args = console_args
        self.template = template

    def get(self):
        data_loader = DataLoader()
        # data_loader.set_vault_password()
        variable_manager = VariableManager(loader=data_loader)

        extra_vars = self.console_args.extra_vars[:]

        extra_vars.append(
            'cluster=' +
            get_cluster_name(
                self.cluster_config_path))

        context_cliargs = dict(context.CLIARGS)
        context_cliargs['extra_vars'] = tuple(extra_vars)

        context.CLIARGS = ImmutableDict(context_cliargs)
        variable_manager._extra_vars = load_extra_vars(
            loader=data_loader)

        variables = variable_manager.get_vars()

        rendered = self.template.render(self.cluster_config_path, variables)

        return yaml.safe_load(rendered)


class ClusterConfigGenerator(object):
    def __init__(self, console_args, cluster_config_path, template):
        self.template = template
        self.cluster_config_path = cluster_config_path
        self.console_args = console_args

    def get(self):
        if os.path.isdir(self.cluster_config_path):
            return {"cluster": None, "inventory": None}

        data_loader = DataLoader()
        # data_loader.set_vault_password('627VR8*;YU99B')
        variable_manager = VariableManager(loader=data_loader)

        extra_vars = self.console_args.extra_vars[:]

        configurations = [
            '@' + config for config in self.cluster_config_path.split(',')]

        extra_vars.append(
            'cluster=' +
            get_cluster_name(
                self.cluster_config_path))
        extra_vars.extend(configurations)

        context_cliargs = dict(context.CLIARGS)
        context_cliargs['extra_vars'] = tuple(extra_vars)

        context.CLIARGS = ImmutableDict(context_cliargs)
        variable_manager._extra_vars = load_extra_vars(
            loader=data_loader)

        read_variables = variable_manager.get_vars()

        templar = Templar(data_loader, variables=read_variables)

        for filter in self.template.filter_plugin_loader.all():
            templar.environment.filters.update(filter.filters())

        return templar.template(read_variables, fail_on_undefined=True)
