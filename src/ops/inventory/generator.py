# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import os
import tempfile
import uuid
from distutils.dir_util import copy_tree

import ansible.inventory as ansible_inventory
import ansible.vars as ansible_vars
from . import caching
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import display
from ansible.vars.manager import VariableManager
from ops import OpsException
import logging


logger = logging.getLogger(__name__)


class CachedInventoryGenerator(object):
    def __init__(self, base_inventory_generator, cluster_config, ops_config):
        self.inventory_generator = base_inventory_generator
        self.ops_config = ops_config
        self.cluster_config = cluster_config
        self.cache_location = self.location()

    def _get_cache(self):
        if 'REFRESH_CACHE' in os.environ:
            if os.environ['REFRESH_CACHE'] == 'True':
                return False

        if not self.ops_config.get('inventory.max_age'):
            logger.info("Inventory caching disabled")
            return False

        max_age = self.ops_config.get('inventory.max_age')
        logger.info(
            "Checking cache from max_age=%s, location=%s" %
            (max_age, self.cache_location))
        if caching.is_valid(self.cache_location, int(max_age)):
            res = caching.read(self.cache_location)
            display.display(
                "Loading cached inventory info from: %s" %
                (self.cache_location), color='blue', stderr=True)
            return res

        return False

    def _save_cache(self, inventory_path, ssh_config_path, errors):
        max_age = self.ops_config.get('inventory.max_age')
        if not max_age:
            return inventory_path, ssh_config_path

        display.display("Caching inventory location to %s for %d seconds" % (self.cache_location, max_age),
                        color='blue', stderr=True)
        caching.write(self.cache_location, dict(
            inventory_path=inventory_path,
            ssh_config_path=ssh_config_path,
            errors=errors
        ))

        return inventory_path, ssh_config_path

    def location(self):
        settings = self.cluster_config.get('inventory_settings', {})
        default_cache_dir = self.ops_config.get('cache.dir')
        return settings.get('location', caching.get_cache_path(
            default_cache_dir, self.cluster_config['inventory']))

    def clear_cache(self):
        # Note: This function is not used when --refresh-cache is passed
        cache = self._get_cache()
        if cache:
            display.display(
                "Removing inventory cache %s" %
                self.cache_location,
                stderr=True,
                color='green')
            try:
                os.remove(os.path.expanduser(self.cache_location))
                display.display("Success", color='blue')
            except OSError:
                display.display(
                    "Warning, could not delete cache as it is not there.",
                    color='yellow')

    def generate(self):
        cache = self._get_cache()
        if cache:
            inventory_path, ssh_config_path, errors = cache[
                'inventory_path'], cache['ssh_config_path'], cache['errors']
            self.inventory_generator.display_errors(errors)

            return inventory_path, ssh_config_path

        inventory_path, ssh_config_path = self.inventory_generator.generate()

        return self._save_cache(
            inventory_path, ssh_config_path, self.inventory_generator.errors)


class InventoryGenerator(object):
    def __init__(self, cluster_config, ssh_config_generator,
                 ops_config, inventory_generators=[]):
        self.ssh_config_generator = ssh_config_generator
        self.cluster_config = cluster_config
        self.generators = inventory_generators
        self.cache_dir = ops_config.get('cache.dir')

        self.generated_path = None
        self.ssh_config_path = None
        self.errors = []

    def generate(self):
        if self.generated_path and self.ssh_config_path:
            return self.generated_path, self.ssh_config_path

        caches_dir = os.path.expanduser(self.cache_dir)
        if not os.path.exists(caches_dir):
            os.makedirs(caches_dir)

        base_path = tempfile.mkdtemp("", "inventory", caches_dir)
        inventory_path = base_path + '/inventory'
        os.mkdir(inventory_path)

        display.display(
            "Generating inventory to %s" %
            inventory_path,
            color='yellow',
            stderr=True)

        if 'inventory' not in self.cluster_config:
            raise Exception(
                "No inventory entry found in configuration for " +
                self.cluster_config['cluster'])

        errors = []
        inventory_settings = self.cluster_config.get('inventory', {})

        if not isinstance(inventory_settings, list):
            raise OpsException(
                "Inventory settings must be a list of dict entries")

        for entry in inventory_settings:
            found_generator = False

            for generator in self.generators:
                if generator.supports(entry):
                    try:
                        generator.generate(inventory_path, entry)
                    except KeyError as e:
                        error = 'Required key %s not found' % e
                        errors.append(dict(entry=entry, error=error))
                    found_generator = True
                    break

            if not found_generator:
                raise Exception(
                    "Cannot find generator for inventory entry %s" %
                    entry)

        self.ssh_config_path = self.ssh_config_generator.generate(base_path)
        self.generated_path = inventory_path
        self.errors = errors

        self.display_errors(errors)

        return self.generated_path, self.ssh_config_path

    @staticmethod
    def display_errors(errors):
        for error in errors:
            display.display(
                "%s for entry %s" %
                (error['error'],
                 error['entry']),
                stderr=True,
                color='yellow')


class DirInventoryGenerator(object):
    """ Just copies the full path specified in path into the inventory dir """

    def __init__(self, root_dir):
        self.root_dir = root_dir

    def supports(self, config):
        return config.get('directory') is not None

    def generate(self, dest, config):
        copy_tree(self.root_dir + '/' + config['directory'], dest)


class PluginInventoryGenerator(object):
    template = """#!/usr/bin/env python
# CONFIG: {config}
# PLUGIN PATH: {plugin_path}
print(\"\"\"
{json_content}
\"\"\")
"""

    def __init__(self, cluster_name, inventory_plugins):
        self.cluster_name = cluster_name
        self.inventory_plugins = inventory_plugins

    def supports(self, config):
        return config.get('plugin') is not None

    def generate(self, dest, config):
        plugins = {
            plugin.__name__: plugin for plugin in self.inventory_plugins}
        plugin = plugins[config.get('plugin')]

        inventory_json = plugin(config.get('args', {}))

        script_content = self.template.format(
            config=repr(config),
            plugin_path=plugin.__module__,
            json_content=inventory_json
        )
        script_dest = "%s/%s-%s.sh" % (dest, self.cluster_name, uuid.uuid4())

        with open(script_dest, 'w+') as f:
            f.write(script_content)
            os.fchmod(f.fileno(), 0o500)


class ShellInventoryGenerator(object):
    """
    Creates a script to be executed by Ansible inventory mechanism and places it in
    the temp directory
    """

    template = """#!/bin/bash

# Store the script inventory output in the cache directory for caching
CURRENT_DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )"
INVENTORY_CACHE="${{CURRENT_DIR}}/.inventory_cache"

cd {root_dir}
if [ -f "$INVENTORY_CACHE" ]; then
  cat "$INVENTORY_CACHE"
else
  {script} | tee "$INVENTORY_CACHE"
  if [ ${{PIPESTATUS[0]}} -ne 0 ]; then
    rm "$INVENTORY_CACHE"
  fi
fi
"""

    def __init__(self, cluster_config_path, cluster_name):
        self.cluster_name = cluster_name

        clusters_dirname = os.path.dirname(cluster_config_path)
        self.legacy_root_dir = os.path.realpath(
            os.path.join(clusters_dirname, ".."))

    def supports(self, config):
        return config.get('script') is not None

    def get_script(self, config):
        command = config['script']
        for key, value in config.get('args', {}).items():
            command += " --%s=%s " % (key, value)

        return command

    def generate(self, dest, config):
        script_content = self.template.format(
            root_dir=self.legacy_root_dir,
            script=self.get_script(config)
        )

        script_dest = "%s/%s.sh" % (dest, self.cluster_name)

        with open(script_dest, 'w+') as f:
            f.write(script_content)
            os.fchmod(f.fileno(), 0o500)


class AnsibleInventory(object):

    def __init__(self, inventory_generator):
        """
        :type inventory_generator: ops.inventory.generator.InventoryGenerator
        """

        self.inventory_generator = inventory_generator
        self.generated_path, self.ssh_config_path = inventory_generator.generate()

        # clean up variables cache for tests
        ansible_vars.VARIABLE_CACHE = dict()
        ansible_vars.HOSTVARS_CACHE = dict()
        ansible_inventory.HOSTS_PATTERNS_CACHE = dict()

        loader = DataLoader()
        loader.set_basedir(self.generated_path)
        self.inventory = InventoryManager(
            loader=loader, sources=[
                self.generated_path])
        self.variable_manager = VariableManager(
            loader=loader, inventory=self.inventory)

    def get_hosts(self, limit):
        return self.inventory.get_hosts(limit)

    def get_host(self, host):
        return self.inventory.get_host(str(host))

    def get_vars(self, host):
        return self.inventory.get_vars(str(host))

    def get_ssh_config(self):
        return self.ssh_config_path
