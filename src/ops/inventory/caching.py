# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import hashlib
import json
import os
import time

from six import PY3


def cache_callback_result(directory, func, max_age, cache_key_args):
    directory = os.path.expanduser(directory)
    path = get_cache_path(directory, cache_key_args)
    if is_valid(path, max_age):
        return read(path)

    return write(path, func())


def get_cache_path(dir, args):
    m = hashlib.md5()
    json_dump = json.dumps(args)
    if PY3:
        json_dump = json_dump.encode('utf-8')
    m.update(json_dump)

    return os.path.join(dir, m.hexdigest())


def is_valid(filename, max_age):
    """ Determines if the cache files have expired, or if it is still valid """

    filename = os.path.expanduser(filename)
    if os.path.isfile(filename):
        mod_time = os.path.getmtime(filename)
        current_time = time.time()
        if (mod_time + max_age) > current_time:
            return True

    return False


def write(filename, data):
    """ Writes data in JSON format to a file """

    json_data = json.dumps(data, sort_keys=True, indent=2)
    cache = open(os.path.expanduser(filename), 'w')
    cache.write(json_data)
    cache.close()

    return data


def read(filename):
    """ Reads the inventory from the cache file and returns it as a JSON
    object """

    cache = open(os.path.expanduser(filename), 'r')
    json_inventory = cache.read()
    return json.loads(json_inventory)
