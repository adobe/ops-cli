# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from ops.inventory.ec2inventory import Ec2Inventory


def ec2(args):
    filters = args.get('filters', {})
    bastion_filters = args.get('bastion', {})

    if args.get('cluster') and not args.get('filters'):
        filters['tag:cluster'] = args.get('cluster')

    if args.get('cluster') and not args.get('bastion'):
        bastion_filters['tag:cluster'] = args.get('cluster')
        bastion_filters['tag:role'] = 'bastion'

    return Ec2Inventory(boto_profile=args['boto_profile'],
                        regions=args['region'],
                        filters=filters,
                        bastion_filters=bastion_filters).get_as_json()
