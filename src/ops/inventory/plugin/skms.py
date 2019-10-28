# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from ops.cli import display
from ansible.utils.color import stringc
from ops.inventory.SKMS import WebApiClient
from ansible.playbook.play import display
import sys
import yaml
import os.path


def skms(args):
    """
    Example cluster file:

    inventory:
      - plugin: skms
        args:
          skms:
            endpoint: api.skms.mycompany.com
          environment: 'Solution Name - OR1 - Production'
          strip:
            device_service: 'Solution Name - '
            environment: 'Solution Name - OR1 - '
            hostname: .solution.mycompany.net

    Example credentials file (located at ~/.skms/credentials.yaml):

    endpoint: "api.skms.mycompany.com"
    username: "<username>"
    password: "<password>"
    """

    credentials_file = "%s/.skms/credentials.yaml" % os.path.expanduser('~')
    if os.path.isfile(credentials_file):
        file_stream = open(credentials_file, "r")
        docs = yaml.safe_load_all(file_stream)
        for doc in docs:
            args['skms']['username'] = doc['username']
            args['skms']['password'] = doc['password']
    else:
        display(
            stringc(
                'Credentials file does not exist: %s' %
                credentials_file,
                'red'))
        sys.exit(1)

    conn = WebApiClient(
        args['skms']['username'],
        args['skms']['password'],
        args['skms']['endpoint'])
    query = {'request_arr': []}
    query_list = []
    query_list.append('details')
    query_list.append('attributes')

    query['request_arr'].append({'object': 'DeviceDao', 'method': 'search', 'parameters': {
                                'query': "SELECT device_id, name, operating_system.display_name "
                                "as operating_system, device_service.full_name AS device_service, "
                                "environment.full_name AS environment, primary_ip_address.ip_address "
                                "AS primary_ip_address WHERE environment.full_name = \"%s\" PAGE 1, 5000"
                                % args['environment']}})

    conn.send_request('SkmsWebApi', 'performMultipleRequests', query)

    response = conn.get_response_dictionary()

    if response['status'] == 'error':
        display(stringc('SKMS query produced an error: %s' % response, 'red'))
        sys.exit(1)

    if 'device_service' in args['strip']:
        device_service_strip = args['strip']['device_service']
    else:
        device_service_strip = ''

    if 'environment' in args['strip']:
        environment_strip = args['strip']['environment']
    else:
        environment_strip = ''

    if 'hostname' in args['strip']:
        hostname_strip = args['strip']['hostname']
    else:
        hostname_strip = ''

    dictionary_of_hosts = {
        '_meta': {
            'hostvars': {}
        }
    }

    for info in response['data']['result_arr'][0]['data']['results']:
        # Raising warning when primary ip is unavailable !!!
        if info['primary_ip_address'] is None:
            display.display(
                "[WARN] missing primary_ip_address, ignoring following host SKMS data:\n" +
                str(info),
                color='yellow')
            continue
        if info['operating_system'] is None:
            info['operating_system'] = ''
        info['computer_name'] = info['name']
        info['location_name'] = info['environment'].split('-')[1].strip()
        info['name'] = info['name'].replace(hostname_strip, '')
        info['environment'] = info['environment'].replace(
            environment_strip, '')
        info['owner'] = environment_strip.split('-')[0].strip()
        info['site'] = info['name'].split('-')[0]
        info['cluster'] = '-'.join(info['name'].split('-')[:2])

        # step through device services to add them as groups
        for device_service in info['device_service']:
            device_service = device_service.replace(
                device_service_strip, '').encode('utf-8')

            # add device service to top-level dictionary as a group
            if device_service not in dictionary_of_hosts:
                dictionary_of_hosts[device_service] = {"hosts": []}
            # add host to array of that device service group
            if info['name'] not in dictionary_of_hosts[device_service]['hosts']:
                dictionary_of_hosts[device_service]['hosts'].append(
                    info['name'].encode('utf-8'))

        # add environment to top-level dictionary as a group
        if info['environment'] not in dictionary_of_hosts:
            dictionary_of_hosts[info['environment'].encode(
                'utf-8')] = {"hosts": []}
        # add host to array of that environment group
        if info['name'] not in dictionary_of_hosts[info['environment']]['hosts']:
            dictionary_of_hosts[info['environment']]['hosts'].append(
                info['name'].encode('utf-8'))

        # add primary_ip_address to top-level dictionary as a group
        if info['primary_ip_address'] not in dictionary_of_hosts:
            dictionary_of_hosts[info['primary_ip_address'].encode(
                'utf-8')] = {"hosts": []}
        if info['name'] not in dictionary_of_hosts[info['primary_ip_address']]['hosts']:
            dictionary_of_hosts[info['primary_ip_address']
                                ]['hosts'].append(info['name'].encode('utf-8'))

        # add owner to top-level dictionary as a group
        if info['owner'] not in dictionary_of_hosts:
            dictionary_of_hosts[info['owner'].encode('utf-8')] = {"hosts": []}
        if info['name'] not in dictionary_of_hosts[info['owner']]['hosts']:
            dictionary_of_hosts[info['owner']]['hosts'].append(
                info['name'].encode('utf-8'))

        # add site to top-level dictionary as a group
        if info['site'] not in dictionary_of_hosts:
            dictionary_of_hosts[info['site'].encode('utf-8')] = {"hosts": []}
        if info['name'] not in dictionary_of_hosts[info['site']]['hosts']:
            dictionary_of_hosts[info['site']]['hosts'].append(
                info['name'].encode('utf-8'))

        # add cluster to top-level dictionary as a group
        if info['cluster'] not in dictionary_of_hosts:
            dictionary_of_hosts[info['cluster'].encode(
                'utf-8')] = {"hosts": []}
        if info['name'] not in dictionary_of_hosts[info['cluster']]['hosts']:
            dictionary_of_hosts[info['cluster']]['hosts'].append(
                info['name'].encode('utf-8'))

        # tie some extra information to hostname in the meta variables
        dictionary_of_hosts['_meta']['hostvars'][info['name'].encode('utf-8')] = {
            'ec2_id': info['device_id'].encode('utf-8'),
            'ansible_ssh_host': info['primary_ip_address'].encode('utf-8'),
            'ansible_host': info['primary_ip_address'].encode('utf-8'),
            'computer_name': info['computer_name'].encode('utf-8'),
            'location': info['location_name'].encode('utf-8'),
            'name': info['name'].split('.')[0].encode('utf-8'),
            'operating_system': info['operating_system'].encode('utf-8'),
            'private_ip': info['primary_ip_address'].encode('utf-8'),
            'tags': {
                'Adobe:Environment': info['environment'].encode('utf-8'),
                'Adobe:Owner': info['owner'].encode('utf-8'),
                'CMDB_device_service': device_service.encode('utf-8'),
                'CMDB_environment': info['environment'].encode('utf-8'),
                'CMDB_hostname': info['name'].split('.')[0].encode('utf-8'),
                'cluster': info['cluster'].encode('utf-8'),
                'environment': info['environment'].encode('utf-8'),
                'role': device_service.encode('utf-8'),
                'site': info['site'].encode('utf-8'),
            }
        }

    return dictionary_of_hosts
