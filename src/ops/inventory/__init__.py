# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import sys
from shutil import which
from .ec2inventory import Ec2Inventory

def display(msg, **kwargs):
    # use ansible pretty printer if available
    try:
        from ansible.playbook.play import display
        display.display(msg, **kwargs)
    except ImportError:
        print(msg)

def err(msg):
    display(str(msg), stderr=True, color='red')

def check_if_teleport_binary_installed():
    if which("tsh") is None:
        err('tsh binary needs to be installed for Teleport to work!')
        sys.exit(2)