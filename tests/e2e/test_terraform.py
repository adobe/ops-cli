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

current_dir = os.path.dirname(__file__)


@pytest.fixture
def app():
    def _app(args):
        return AppContainer(args)

    return _app


def test_terraform_templating_for_file_plugin(capsys, app):
    app(['--root-dir', current_dir + '/fixture/terraform', 'clusters/prod/test.yaml', 'terraform', 'template']).run()

    out, err = capsys.readouterr()
    print(out)
    print(err)
    assert 'my_user_data' in out


def test_terraform_plan(capsys, app):
    container = app(['--root-dir', current_dir + '/fixture/terraform', 'clusters/prod/test.yaml', 'terraform', 'plan'])
    command = container.run()


    # we have the terraform plan command
    assert 'terraform plan' in command['command']

    # we have a post_action -> the delete command
    assert len(command['post_actions']) == 1

    # when we call the post actions
    container.execute(command)
    assert not os.path.isfile(current_dir + '/fixture/terraform/terraform/main/main.tf')


def test_terraform_apply(capsys, app):
    def terraform(*args):
        a = ['--root-dir', current_dir + '/fixture/terraform', 'clusters/prod/test.yaml']
        a.extend(args)
        container = app(a)
        container.execute(container.run())

    terraform('terraform', 'plan')
    # terraform('terraform', 'apply')
    # terraform('terraform', 'output', '--var', 'user_data_out')
