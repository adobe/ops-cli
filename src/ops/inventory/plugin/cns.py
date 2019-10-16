# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import json

from .ec2 import ec2


def cns(args):
    result = {}

    if 'clusters' not in args:
        raise Exception('clusters entry is missing in the cns plugin args')

    for cluster in args['clusters']:
        region = cluster['region']
        profile = cluster['boto_profile']
        for cns_cluster in cluster['names']:
            jsn = ec2(dict(
                region=region,
                boto_profile=profile,
                cache=args.get('cache', 3600 * 24),
                filters={
                    'tag:cluster': cns_cluster
                },
                bastion={
                    'tag:cluster': cns_cluster,
                    'tag:role': 'bastion'
                }
            ))

            merge_inventories(result, json.loads(jsn))

    return json.dumps(result, sort_keys=True, indent=2)


def merge_inventories(a, b):
    for k, v in b.items():
        if not a.get(k):
            a[k] = b[k]
        elif isinstance(a[k], list):
            a[k].extend(b[k])
        elif k == '_meta':
            a[k]['hostvars'].update(b[k]['hostvars'])
