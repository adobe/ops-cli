# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import os
from subprocess import Popen, PIPE
import sys


def get_output(command, trim=True):
    out = Popen(command, shell=True, stdout=PIPE).communicate()[0]
    if trim:
        out = out.strip()

    return out


def display(msg, **kwargs):
    # use ansible pretty printer if available
    try:
        from ansible.playbook.play import display
        display.display(msg, **kwargs)
    except ImportError:
        print(msg)


def err(msg):
    display(str(msg), stderr=True, color='red')


def get_config_value(config, key):
    try:
        return config[key]
    except KeyError as e:
        err("You must set the %s value in %s.yaml or in the cli as an extra variable: -e %s=value" %
            (e.message, config['cluster'], e.message))
        sys.exit(1)
