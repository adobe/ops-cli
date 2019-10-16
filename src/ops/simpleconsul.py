# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

#!/usr/bin/env python

"""
Very simple wrapper class to access consul data
"""

import re
import consul
import hashmerge

from six import iteritems

DEFAULT_CONNECT = {
    'host': '127.0.0.1',
    'port': 8500,
    'scheme': 'http'
}

DEFAULT_PARAMS = {
    'token': None,
    'consistency': 'default',
    'dc': None,
    'verify': True
}


class SimpleConsul(object):
    """ Simple wrapper class for interacting with Consul. Focused mainly on KV operations"""

    consul_params = {}
    conn = None

    def __init__(self, consul_url='http://127.0.0.1:8500',
                 token=None, consistency='default',
                 dc=None, verify=True):
        """
        Assemble parameters for connecting to consul, fill in with defaults where
        we do not receive any,then connect to consul
        """
        self.consul_params = {}
        self.consul_params.update(DEFAULT_CONNECT)
        self.consul_params.update(DEFAULT_PARAMS)
        self.consul_params.update(
            self._parse_connect_url(consul_url))
        if token:
            self.consul_params['token'] = token
        if consistency:
            self.consul_params['consistency'] = consistency
        if dc:
            self.consul_params['dc'] = dc
        if verify:
            self.consul_params['verify'] = verify
        self.conn = consul.Consul(**self.consul_params)
        self.conn.kv.get("just-fail-if-we-cannot-connect-to-consul")

    @staticmethod
    def _parse_connect_url(url):
        """Get host port and scheme from an url"""
        ret = {}
        s_res = re.match(r'(http|https)://([\w\-\.]+)+(:(\d+)){0,1}', str(url))
        if s_res:
            keys = 'scheme', 'host', 'skip', 'port'
            ret = {
                keys[i]: s_res.group(
                    i +
                    1) for i in range(
                    0,
                    4) if s_res.group(
                    i +
                    1)}
            ret.pop('skip', True)
        return ret

    def get(self, key, recurse=False):
        """Read a key"""
        merger = hashmerge.HashMerge(hashmerge.RIGHT_PRECEDENT)
        index, data = self.conn.kv.get(key, recurse=False)
        if data:
            single_value = data.get('Value', None)
        else:
            single_value = None
        if not recurse:
            return single_value
        aggregated = {}
        keys_dict = {}
        index, keys_list = self.conn.kv.get(key + '/', recurse=recurse)
        if keys_list:
            keys_dict = {i['Key']: i['Value'] for i in keys_list}
        for k, v in iteritems(keys_dict):
            tmp = {}
            path_atoms = k.split('/')
            leaf = path_atoms.pop()
            if leaf == '':
                tmp = {}
            else:
                tmp = {leaf: v}
            for atom in reversed(path_atoms):
                tmp = {atom: tmp}
            aggregated = merger.merge(aggregated, tmp)
        return aggregated or single_value

    def put(self, key, value):
        """Put a key"""
        if isinstance(value, (int, str)):
            self.conn.kv.put(key, str(value), cas=None,
                             flags=None, acquire=None, release=None,
                             token=None, dc=None)
        elif isinstance(value, list):
            for item in value:
                self.conn.kv.put(key, item, "True")
        elif isinstance(value, dict):
            for k, v in iteritems(value):
                self.put(key + '/' + k, v)
