# This Python file uses the following encoding: utf-8
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
from six import PY3

from ops.main import AppContainer
from simpledi import *

current_dir = os.path.dirname(__file__)


def app(*args):
    app = AppContainer(args)

    def test_plugin(inventory_opts):
        return """
                    {
                      "bastion": ["bastion.host"],
                      "nat": ["bastion.host"],
                      "web": [
                        "web1.host",
                        "web2.host"
                      ]
                    }
                """

        # we configure the plugin test_plugin

    inventory_plugins = ListInstanceProvider(instance(test_plugin))
    app.inventory_plugins = inventory_plugins

    return app


def run(*args):
    return app(*args).run()


def test_plugin_generator(capsys):
    # we run the inventory
    run(current_dir + '/fixture/inventory/clusters/plugin_generator.yaml', 'inventory')

    # we should have the 3 hosts in the inventory output
    out, err = capsys.readouterr()
    print(out)
    print(err)
    assert 'bastion.host' in out
    assert 'web1.host' in out
    assert 'web2.host' in out


def test_inventory_limit(capsys):
    # when we run with limit, then we should have only one host
    run(current_dir + '/fixture/inventory/clusters/plugin_generator.yaml', 'inventory', '--limit', 'bastion')
    out, err = capsys.readouterr()
    print(out)
    print(err)
    assert 'bastion.host' in out
    assert 'web1.host' not in out


if not PY3:
    def test_inventory_limit_unicode_dash():
        with pytest.raises(UnicodeDecodeError):
            run(current_dir + '/fixture/inventory/clusters/plugin_generator.yaml', 'inventory', '––limit', 'bastion')
