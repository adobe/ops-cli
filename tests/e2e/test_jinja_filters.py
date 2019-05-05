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
from ops.main import AppContainer
from simpledi import *

@pytest.fixture
def app():
    def _app(args):
        return AppContainer(args)
    return _app

current_dir = os.path.dirname(__file__)

def test_loading_of_modules(capsys, app):
    root_dir = current_dir + '/fixture/ansible'
    container = app(['-vv', '--root-dir', root_dir, 'clusters/test_filters.yaml', 'play',
                       'playbooks/play_module.yaml'])

    code = container.execute(container.run(), pass_trough=False)
    out, err = capsys.readouterr()
    assert code is 0

    container.cluster_config['test_standard_filters'] == '6'
    container.cluster_config['test_custom_filters'] == 'filtered: value'
