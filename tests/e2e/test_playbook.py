#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

# coding=utf-8
import os
import pytest
from ops.main import AppContainer


def app(args):
    return AppContainer(args)

current_dir = os.path.dirname(__file__)


def test_loading_of_modules_and_extensions():
    root_dir = current_dir + '/fixture/ansible'
    container = app(['-vv', '--root-dir', root_dir, 'clusters/test.yaml', 'play',
                       'playbooks/play_module.yaml'])

    command = container.run()

    out, err = container.execute(command, pass_trough=False)
    print out, err

    # the filter plugins work
    assert '"msg": "filtered: filter_this"' in out

    # custom modules are interpreted
    assert '"the_module_works": "yep"' in out

    # cluster is present as a variable in the command line
    assert '-e cluster=test' in command['command']


def test_ssh_user_unicode_dash():
    with pytest.raises(UnicodeDecodeError):
        root_dir = current_dir + '/fixture/ansible'
        container = app([u'–vv', '--root-dir', root_dir, 'clusters/test.yaml', 'play',
                           'playbooks/play_module.yaml'])

        container.run()
