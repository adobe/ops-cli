# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.


from ops.inventory.azurerm import *
from ansible.playbook.play import display
from six import iteritems


class DictGlue(object):
    def __init__(self, data={}):
        self.__dict__.update(data)


class EnvironmentMissingException(Exception):
    pass


class OpsAzureInventory(AzureInventory):
    """
    We inherit from the original implementation and override what we need here
    The original implementation is intended to be called by ansible and has different parameter semantics
    we override them here so that in the future we can update the azurerm independently (hopefully)
    """

    def __init__(self, args={}):
        self._dict_args = {
            'list': True,
            'debug': False,
            'host': None,
            'pretty': False,
            'profile': None,
            'subscription_id': None,
            'client_id': None,
            'secret': None,
            'tenant': None,
            'ad_user': None,
            'password': None,
            'resource_groups': None,
            'tags': None,
            'locations': None,
            'no_powerstate': False,
            'bastion_tag': 'Adobe:Class'
        }
        if not HAS_AZURE:
            raise HAS_AZURE_EXC

        self._dict_args.update(args)
        if self._dict_args['subscription_id'] is not None:
            self._dict_args.update(
                {'subscription_id': str(self._dict_args['subscription_id'])})
        self._args = DictGlue(self._dict_args)
        rm = AzureRM(self._args)

        self._compute_client = rm.compute_client
        self._network_client = rm.network_client
        self._resource_client = rm.rm_client
        self._security_groups = None
        self.resource_groups = []
        self.tags = None
        self.locations = None
        self.replace_dash_in_groups = False
        self.group_by_resource_group = True
        self.group_by_location = True
        self.group_by_security_group = False
        self.group_by_tag = True
        self.include_powerstate = True

        self._inventory = dict(
            _meta=dict(
                hostvars=dict()
            ),
            azure=[]
        )
        self._get_settings()

        if self._args.resource_groups:
            self.resource_groups = self._args.resource_groups.split(',')

        if self._args.tags:
            self.tags = self._args.tags.split(',')

        if self._args.locations:
            self.locations = self._args.locations.split(',')

        if self._args.no_powerstate:
            self.include_powerstate = False

        self.get_inventory()

        bastions = {}
        for host, hostvars in iteritems(self._inventory['_meta']['hostvars']):
            if ('role' in hostvars['tags'] and hostvars['tags']['role'] == 'bastion') or \
                    (self._args.bastion_tag in hostvars['tags'] and
                        hostvars['tags'][self._args.bastion_tag] == 'bastion'):
                if hostvars['public_ip'] is not None:
                    bastion_ip = hostvars['public_ip']
                    location = hostvars['location']
                    bastions[location] = bastion_ip
                    self._inventory['_meta']['hostvars'][host]['ansible_ssh_host'] = bastion_ip
                else:
                    display.display(
                        "Warning, bastion host found but has no public IP (is the host stopped?)",
                        color='yellow')

        if bastions:
            for host, hostvars in iteritems(
                    self._inventory['_meta']['hostvars']):
                if ('role' in hostvars['tags'] and
                    hostvars['tags']['role'] == 'bastion') or \
                        (self._args.bastion_tag in hostvars['tags'] and
                         hostvars['tags'][self._args.bastion_tag] == 'bastion'):
                    pass
                else:
                    private_ip = hostvars['private_ip']
                    self._inventory['_meta']['hostvars'][host]['ansible_ssh_host'] = \
                        bastions[hostvars['location']] + '--' + private_ip

    def get_as_json(self, pretty=False):
        return self._json_format_dict(pretty=pretty)

    def _selected_machines(self, virtual_machines):
        selected_machines = []
        for machine in virtual_machines:
            # explicit chosen host
            if self._args.host and self._args.host == machine.name:
                selected_machines.append(machine)
            # filter only by tags
            if self.tags and not self.locations and self._tags_match(
                    machine.tags, self.tags):
                selected_machines.append(machine)
            # filter only by location
            if self.locations and not self.tags and machine.location in self.locations:
                selected_machines.append(machine)
            # filter by both location and tags
            if self.locations and self.tags and self._tags_match(
                    machine.tags, self.tags) and machine.location in self.locations:
                selected_machines.append(machine)
        return selected_machines


def azr(args={}):
    """Eventual filtering will be done here after we will define how we group and tag resources"""
    return OpsAzureInventory(args).get_as_json(pretty=True)
