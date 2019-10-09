# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from jinja2 import FileSystemLoader, Environment, StrictUndefined, Undefined, DebugUndefined
from jinja2.loaders import ChoiceLoader

from ansible.plugins.loader import PluginLoader


class Template(object):

    def __init__(self, root_dir, ops_config):
        loader = ChoiceLoader([
            FileSystemLoader(root_dir),
            FileSystemLoader("/")
        ])

        mode = ops_config.get('jinja2.undefined')
        undefined = Undefined
        if mode == 'StrictUndefined':
            undefined = StrictUndefined
        elif mode == 'DebugUndefined':
            undefined = DebugUndefined

        self.env = Environment(loader=loader, undefined=undefined)

        self.filter_plugin_loader = PluginLoader(
            'FilterModule',
            'ansible.plugins.filter',
            ops_config.ansible_filter_plugins.split(':'),
            'filter_plugins'
        )

        for filter in self.filter_plugin_loader.all():
            self.env.filters.update(filter.filters())

    def render(self, source, vars):
        jinja_template = self.env.get_template(source)

        return jinja_template.render(**vars)
