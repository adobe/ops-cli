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

import boto3
from botocore.exceptions import NoRegionError, NoCredentialsError, PartialCredentialsError


class Ec2Inventory(object):
    @staticmethod
    def _empty_inventory():
        return {"_meta": {"hostvars": {}}}

    def __init__(self, boto_profile, regions, filters=None, bastion_filters=None):

        self.filters = filters or []
        self.regions = regions.split(',')
        self.boto_profile = boto_profile
        self.bastion_filters = bastion_filters or []
        self.group_callbacks = []
        self.boto3_session = self.create_boto3_session(boto_profile)

        # Inventory grouped by instance IDs, tags, security groups, regions,
        # and availability zones
        self.inventory = self._empty_inventory()

        # Index of hostname (address) to instance ID
        self.index = {}

    def create_boto3_session(self, profile_name):
        try:
            # Use the profile to create a session
            session = boto3.Session(profile_name=profile_name)

            # Verify region
            if not self.regions:
                if not session.region_name:
                    raise NoRegionError
                self.regions = [session.region_name]

        except NoRegionError:
            sys.exit(f"Region not specified and could not be determined for profile: {profile_name}")
        except (NoCredentialsError, PartialCredentialsError):
            sys.exit(f"Credentials not found or incomplete for profile: {profile_name}")
        except Exception as e:
            sys.exit(f"An error occurred: {str(e)}")
        return session

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

    def find_bastion_box(self, ec2_client):
        """
        Find ips for the bastion box
        """

        if not self.bastion_filters:
            return

        self.bastion_filters.append({'Name': 'instance-state-name', 'Values': ['running']})

        reservations = ec2_client.describe_instances(Filters=self.bastion_filters)['Reservations']
        for reservation in reservations:
            for instance in reservation['Instances']:
                return instance['PublicIpAddress']

    def do_api_calls_update_cache(self):
        """ Do API calls to each region, and save data in cache files """

        for region in self.regions:
            self.get_instances_by_region(region)

    def get_instances_by_region(self, region):
        """Makes an AWS EC2 API call to the list of instances in a particular
        region
        """
        ec2_client = self.boto3_session.client('ec2', region_name=region)

        reservations = ec2_client.describe_instances(Filters=self.filters)['Reservations']

        bastion_ip = self.find_bastion_box(ec2_client)
        instances = []
        for reservation in reservations:
            instances.extend(reservation['Instances'])

        # sort the instance based on name and index, in this order
        def sort_key(instance):
            name = next((tag['Value'] for tag in instance.get('Tags', [])
                         if tag['Key'] == 'Name'), '')
            return "{}-{}".format(name, instance['InstanceId'])

        for instance in sorted(instances, key=sort_key):
            self.add_instance(bastion_ip, instance, region)

    def get_instance(self, region, instance_id):
        """ Gets details about a specific instance """
        ec2_client = self.boto3_session.client('ec2', region_name=region)
        # connect_to_region will fail "silently" by returning None if the
        # region name is wrong or not supported
        if ec2_client is None:
            sys.exit(
                "region name: %s likely not supported, or AWS is down. "
                "connection to region failed." % region
            )

        reservations = ec2_client.describe_instances(InstanceIds=[instance_id])['Reservations']
        for reservation in reservations:
            for instance in reservation['Instances']:
                return instance

    def add_instance(self, bastion_ip, instance, region):
        """
        :type instance: dict
        """

        # Only want running instances unless all_instances is True
        if instance['State']['Name'] != 'running':
            return

        # Use the instance name instead of the public ip
        dest = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), instance.get('PublicIpAddress'))
        if not dest:
            return

        if bastion_ip and bastion_ip != instance.get('PublicIpAddress'):
            ansible_ssh_host = bastion_ip + "--" + instance.get('PrivateIpAddress')
        elif instance.get('PublicIpAddress'):
            ansible_ssh_host = instance.get('PublicIpAddress')
        else:
            ansible_ssh_host = instance.get('PrivateIpAddress')

        # Add to index and append the instance id afterwards if it's already
        # there
        if dest in self.index:
            dest = dest + "-" + instance['InstanceId'].replace("i-", "")

        self.index[dest] = [region, instance['InstanceId']]

        # group with dynamic groups
        for grouping in set(self.group_callbacks):
            given_groups = grouping(instance)
            for group in given_groups:
                if group:
                    self.push(self.inventory, group, dest)

        # Group by all tags
        for tag in instance.get('Tags', []):
            if tag['Value']:
                self.push(self.inventory, tag['Value'], dest)

        # Inventory: Group by region
        self.push(self.inventory, region, dest)

        # Put the ip in a group just to find it in the ssh connection
        self.push(self.inventory, ansible_ssh_host, dest)

        # Inventory: Group by availability zone
        self.push(self.inventory, instance['Placement']['AvailabilityZone'], dest)

        self.inventory["_meta"]["hostvars"][dest] = self.get_host_info_dict_from_instance(instance)
        self.inventory["_meta"]["hostvars"][dest]['ansible_ssh_host'] = ansible_ssh_host

    def get_host_info_dict_from_instance(self, instance):
        instance_vars = {}
        for key, value in instance.items():
            safe_key = self.to_safe('ec2_' + key)

            if key == 'State':
                instance_vars['ec2_state'] = value['Name']
                instance_vars['ec2_state_code'] = value['Code']
            elif isinstance(value, (int, bool)):
                instance_vars[safe_key] = value
            elif isinstance(value, str):
                instance_vars[safe_key] = value.strip()
            elif value is None:
                instance_vars[safe_key] = ''
            elif key == 'Placement':
                instance_vars['ec2_placement'] = value['AvailabilityZone']
            elif key == 'Tags':
                for tag in value:
                    tag_key = self.to_safe('ec2_tag_' + tag['Key'])
                    instance_vars[tag_key] = tag['Value']
            elif key == 'SecurityGroups':
                group_ids = [group['GroupId'] for group in value]
                group_names = [group['GroupName'] for group in value]
                instance_vars["ec2_security_group_ids"] = ','.join(group_ids)
                instance_vars["ec2_security_group_names"] = ','.join(group_names)

        instance_vars['private_ip'] = instance.get('PrivateIpAddress', '')
        instance_vars['private_ip_address'] = instance.get('PrivateIpAddress', '')
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
