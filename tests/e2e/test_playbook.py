# This Python file uses the following encoding: utf-8
#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import os
import pytest
from ops import display

from six import PY3

from ops.main import AppContainer
from simpledi import *

@pytest.fixture
def app():
    def _app(args):
        return AppContainer(args)

    return _app

current_dir = os.path.dirname(__file__)


def test_loading_of_modules_and_extensions(capsys, app):
    root_dir = current_dir + '/fixture/ansible'
    container = app(['-vv', '--root-dir', root_dir, 'clusters/test.yaml', 'play',
                       'playbooks/play_module.yaml'])
    command = container.run()
    code = container.execute(command, pass_trough=False)
    out, err = capsys.readouterr()
    display(out, color='gray')
    display(err, color='red')
    assert code is 0

    # the filter plugins work
    assert '"msg": "filtered: filter_this"' in out

    # custom modules are interpreted
    assert '"the_module_works": "yep"' in out

    # cluster is present as a variable in the command line
    assert '-e cluster=test' in command['command']

if not PY3:
    def test_ssh_user_unicode_dash(capsys, app):
        with pytest.raises(UnicodeDecodeError):
            root_dir = current_dir + '/fixture/ansible'
            app([u'–vv', '--root-dir', root_dir, 'clusters/test.yaml', 'play',
                               'playbooks/play_module.yaml']).run()
