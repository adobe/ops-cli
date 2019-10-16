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
from .cns import merge_inventories


def legacy_pcs(args):
    region = args['region']
    boto_profile = args['boto_profile']
    bastion = args['bastion']

    result = {}

    roles = ['pcs', 'tableloader']

    for role in roles:
        jsn = ec2(dict(
            region=region,
            boto_profile=boto_profile,
            filters={
                'tag:CMDB_role': role
            },
            bastion=bastion
        ))

        merge_inventories(result, json.loads(jsn))

    return json.dumps(result, sort_keys=True, indent=2)
