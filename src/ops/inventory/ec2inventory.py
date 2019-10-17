# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import json
import re
import sys
import os

import boto
from boto import ec2
from boto.pyami.config import Config

from six import iteritems, string_types, integer_types


class Ec2Inventory(object):
    def _empty_inventory(self):
        return {"_meta": {"hostvars": {}}}

    def __init__(self, boto_profile, regions, filters={}, bastion_filters={}):

        self.filters = filters
        self.regions = regions.split(',')
        self.boto_profile = boto_profile
        self.bastion_filters = bastion_filters
        self.group_callbacks = []

        # Inventory grouped by instance IDs, tags, security groups, regions,
        # and availability zones
        self.inventory = self._empty_inventory()

        # Index of hostname (address) to instance ID
        self.index = {}

    def get_as_json(self):
        self.do_api_calls_update_cache()
        return self.json_format_dict(self.inventory, True)

    def __str__(self):
        return self.get_as_json()

    def include(self, *args):
        self.includes.extend(args)

    def exclude(self, *args):
        self.excludes.extend(args)

    def group(self, *args):
        self.group_callbacks.extend(args)

    def find_bastion_box(self, conn):
        """
        Find ips for the bastion box
        """

        if not self.bastion_filters.values():
            return

        self.bastion_filters['instance-state-name'] = 'running'

        for reservation in conn.get_all_instances(
                filters=self.bastion_filters):
            for instance in reservation.instances:
                return instance.ip_address

    def do_api_calls_update_cache(self):
        """ Do API calls to each region, and save data in cache files """

        for region in self.regions:
            self.get_instances_by_region(region)

    def get_instances_by_region(self, region):
        """Makes an AWS EC2 API call to the list of instances in a particular
        region
        """

        try:
            cfg = Config()
            cfg.load_credential_file(os.path.expanduser("~/.aws/credentials"))
            cfg.load_credential_file(os.path.expanduser("~/.aws/config"))
            session_token = cfg.get(self.boto_profile, "aws_session_token")

            conn = ec2.connect_to_region(
                region,
                security_token=session_token,
                profile_name=self.boto_profile)

            # connect_to_region will fail "silently" by returning None if the
            # region name is wrong or not supported
            if conn is None:
                sys.exit(
                    "region name: {} likely not supported, or AWS is down. "
                    "connection to region failed.".format(region))

            reservations = conn.get_all_instances(filters=self.filters)

            bastion_ip = self.find_bastion_box(conn)

            instances = []
            for reservation in reservations:
                instances.extend(reservation.instances)

            # sort the instance based on name and index, in this order
            def sort_key(instance):
                name = instance.tags.get('Name', '')
                return "{}-{}".format(name, instance.id)

            for instance in sorted(instances, key=sort_key):
                self.add_instance(bastion_ip, instance, region)

        except boto.provider.ProfileNotFoundError as e:
            raise Exception(
                "{}, configure it with 'aws configure --profile {}'".format(e.message, self.boto_profile))

        except boto.exception.BotoServerError as e:
            sys.exit(e)

    def get_instance(self, region, instance_id):
        """ Gets details about a specific instance """
        conn = ec2.connect_to_region(region)

        # connect_to_region will fail "silently" by returning None if the
        # region name is wrong or not supported
        if conn is None:
            sys.exit(
                "region name: %s likely not supported, or AWS is down. "
                "connection to region failed." % region
            )

        reservations = conn.get_all_instances([instance_id])
        for reservation in reservations:
            for instance in reservation.instances:
                return instance

    def add_instance(self, bastion_ip, instance, region):
        """
        :type instance: boto.ec2.instance.Instance
        """

        # Only want running instances unless all_instances is True
        if instance.state != 'running':
            return

        # Use the instance name instead of the public ip
        dest = instance.tags.get('Name', instance.ip_address)
        if not dest:
            return

        if bastion_ip and bastion_ip != instance.ip_address:
            ansible_ssh_host = bastion_ip + "--" + instance.private_ip_address
        elif instance.ip_address:
            ansible_ssh_host = instance.ip_address
        else:
            ansible_ssh_host = instance.private_ip_address

        # Add to index and append the instance id afterwards if it's already
        # there
        if dest in self.index:
            dest = dest + "-" + instance.id.replace("i-", "")

        self.index[dest] = [region, instance.id]

        # group with dynamic groups
        for grouping in set(self.group_callbacks):
            given_groups = grouping(instance)
            for group in given_groups:
                if group:
                    self.push(self.inventory, group, dest)

        # Group by all tags
        for tag in instance.tags.values():
            if tag:
                self.push(self.inventory, tag, dest)

        # Inventory: Group by region
        self.push(self.inventory, region, dest)

        # Put the ip in a group just to find it in the ssh connection
        self.push(self.inventory, ansible_ssh_host, dest)

        # Inventory: Group by availability zone
        self.push(self.inventory, instance.placement, dest)

        self.inventory["_meta"]["hostvars"][dest] = self.get_host_info_dict_from_instance(
            instance)
        self.inventory["_meta"]["hostvars"][dest]['ansible_ssh_host'] = ansible_ssh_host

    def get_host_info_dict_from_instance(self, instance):
        instance_vars = {}
        for key in vars(instance):
            value = getattr(instance, key)
            key = self.to_safe('ec2_' + key)

            # Handle complex types
            # state/previous_state changed to properties in boto in
            # https://github.com/boto/boto/commit/a23c379837f698212252720d2af8dec0325c9518
            if key == 'ec2__state':
                instance_vars['ec2_state'] = instance.state or ''
                instance_vars['ec2_state_code'] = instance.state_code
            elif key == 'ec2__previous_state':
                instance_vars['ec2_previous_state'] = instance.previous_state or ''
                instance_vars['ec2_previous_state_code'] = instance.previous_state_code
            elif type(value) in integer_types or isinstance(value, bool):
                instance_vars[key] = value
            elif type(value) in string_types:
                instance_vars[key] = value.strip()
            elif value is None:
                instance_vars[key] = ''
            elif key == 'ec2_region':
                instance_vars[key] = value.name
            elif key == 'ec2__placement':
                instance_vars['ec2_placement'] = value.zone
            elif key == 'ec2_tags':
                for k, v in iteritems(value):
                    key = self.to_safe('ec2_tag_' + k)
                    instance_vars[key] = v
            elif key == 'ec2_groups':
                group_ids = []
                group_names = []
                for group in value:
                    group_ids.append(group.id)
                    group_names.append(group.name)
                instance_vars["ec2_security_group_ids"] = ','.join(group_ids)
                instance_vars["ec2_security_group_names"] = ','.join(
                    group_names)
        # add non ec2 prefix private ip address that are being used in cross provider command
        # e.g ssh, sync
        instance_vars['private_ip'] = instance_vars.get(
            'ec2_private_ip_address', '')
        instance_vars['private_ip_address'] = instance_vars.get(
            'ec2_private_ip_address', '')
        return instance_vars

    def get_host_info(self):
        """ Get variables about a specific host """

        if not self.index:
            # Need to load index from cache
            self.load_index_from_cache()

        if not self.host in self.index:
            # try updating the cache
            self.do_api_calls_update_cache()
            if not self.host in self.index:
                # host migh not exist anymore
                return self.json_format_dict({}, True)

        (region, instance_id) = self.index[self.host]

        instance = self.get_instance(region, instance_id)
        return self.json_format_dict(
            self.get_host_info_dict_from_instance(instance), True)

    def push(self, my_dict, key, element):
        """ Push an element onto an array that may not have been defined in
        the dict
        """
        if key == element:
            return
        group_info = my_dict.setdefault(key, [])
        if isinstance(group_info, dict):
            host_list = group_info.setdefault('hosts', [])
            if element not in host_list:
                host_list.append(element)
        else:
            if element not in group_info:
                group_info.append(element)

    def push_group(self, my_dict, key, element):
        """ Push a group as a child of another group. """
        parent_group = my_dict.setdefault(key, {})
        if not isinstance(parent_group, dict):
            parent_group = my_dict[key] = {'hosts': parent_group}
        child_groups = parent_group.setdefault('children', [])
        if element not in child_groups:
            child_groups.append(element)

    def to_safe(self, word):
        """ Converts 'bad' characters in a string to underscores so they can be
        used as Ansible groups
        """

        return re.sub(r"[^A-Za-z0-9\-]", "_", word)

    def json_format_dict(self, data, pretty=True):
        """ Converts a dict to a JSON object and dumps it as a formatted
        string
        """

        if pretty:
            return json.dumps(data, sort_keys=True, indent=2)
        return json.dumps(data)

    def group_by_tag(self, param):
        self.group(lambda instance: [instance.tags.get(param, 'no-' + param)])

        return self
