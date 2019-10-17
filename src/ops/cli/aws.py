# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from . import get_output
from datetime import datetime, timezone


def acess_key(profile):
    return get_output(
        'aws configure get aws_access_key_id --profile %s' % profile)


def secret_key(profile):
    return get_output(
        'aws configure get aws_secret_access_key --profile %s' % profile)


def expiry_dttm(profile):
    return get_output('aws configure get expiry_dttm --profile %s' % profile)


def expiry_dttm_in_minutes(profile):
    diff = (datetime.strptime(expiry_dttm(profile), "%Y-%m-%dT%H:%M:%S%z") - datetime.now(timezone.utc)).total_seconds()

    return int(diff / 60)
