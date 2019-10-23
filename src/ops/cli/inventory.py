# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import yaml
import logging

from ansible.parsing.yaml.dumper import AnsibleDumper
from ansible.utils.color import stringc
from . import display
from .parser import configure_common_arguments, SubParserConfig

logger = logging.getLogger(__name__)

class InventoryParserConfig(SubParserConfig):
    def get_name(self):
        return 'inventory'

    def get_help(self):
        return 'Show current inventory data'

    def configure(self, parser):
        configure_common_arguments(parser)
        parser.add_argument(
            '--refresh-cache',
            action='store_true',
            help="Refresh the cache for the inventory")
        parser.add_argument('--limit', type=str,
                            help='Limit run to a specific server subgroup. Eg: --limit newton-dcs')
        parser.add_argument('--facts', default=False, action='store_true',
                            help='Show inventory facts for the given hosts')

        return parser


class InventoryRunner(object):
    def __init__(self, ansible_inventory, cluster_name):
        """
        :type ansible_inventory: ops.inventory.generator.AnsibleInventory
        """
        self.ansible_inventory = ansible_inventory
        self.cluster_name = cluster_name

    def run(self, args, extra_args):
        logger.info("Found extra_args %s", extra_args)
        for host in self.get_inventory_hosts(args):
            group_names = [group.name for group in host.get_groups()]
            group_names = sorted(group_names)
            group_string = ", ".join(group_names)
            host_id = host.vars.get('ec2_id', '')
            if host_id != '':
                name_and_id = "%s -- %s" % (stringc(host.name,
                                                    'blue'), stringc(host_id, 'blue'))
            else:
                name_and_id = "%s" % stringc(host.name, 'blue')
            display("%s (%s)" % (name_and_id, stringc(group_string, 'green')))
            if args.facts:
                display(self.get_host_facts(host))

    def get_inventory_hosts(self, args):
        limit = args.limit or 'all'

        return self.ansible_inventory.get_hosts(limit)

    def get_host_facts(self, host, indent="\t"):
        vars = host.get_vars()
        ret = yaml.dump(
            vars,
            indent=4,
            allow_unicode=True,
            default_flow_style=False,
            Dumper=AnsibleDumper)
        ret = "\n".join([indent + line for line in ret.split("\n")])

        return ret
