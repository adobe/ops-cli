# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from . import get_output
from shlex import quote


def access_key(profile):
    return get_output(
        'aws configure get aws_access_key_id --profile %s' % quote(profile))


def secret_key(profile):
    return get_output(
        'aws configure get aws_secret_access_key --profile %s' % quote(profile))
