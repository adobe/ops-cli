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
import re

from six import PY3

import test_inventory
import pytest

# bring in the fixtures
app = test_inventory.app
run = test_inventory.run

current_dir = os.path.dirname(__file__)


def test_ssh():
    command = run(current_dir + '/fixture/inventory/clusters/plugin_generator.yaml', 'ssh',
                       'bastion', '--', '-ND', '8157')

    assert re.match('ssh -F .+/ssh.config bastion.host -ND 8157', command['command'])


def test_ssh_scb():
    command = run(current_dir + '/fixture/inventory/clusters/plugin_generator_scb.yaml', 'ssh',
                  'bastion', '--', '-TD', '8157')

    assert re.match(r'ssh -F .+/ssh.config .+bastion.host@scb\.example.com -TD 8157',
                    command['command'])


def test_ssh_scb_noscb():
    command = run(current_dir + '/fixture/inventory/clusters/plugin_generator_scb.yaml', 'ssh',
                  '--noscb', 'bastion', '--', '-TD', '8157')

    assert re.match('ssh -F .+/ssh.config bastion.host -TD 8157', command['command'])
    assert "scb.example.com" not in command['command']


def test_ssh_user():
    command = run(current_dir + '/fixture/inventory/clusters/plugin_generator.yaml', 'ssh',
                       'bastion', '-l', 'remote_user')

    assert re.match('ssh -F .+/ssh.config bastion.host -l remote_user', command['command'])


def test_ssh_scb_user():
    command = run(current_dir + '/fixture/inventory/clusters/plugin_generator_scb.yaml', 'ssh',
                  'bastion', '-l', 'remote_user')

    assert re.match(r'ssh -F .+/ssh.config remote_user@bastion.host@scb\.example.com '
                    r'-l remote_user', command['command'])


def test_ssh_scb_user_ssh_dest_user():
    command = run(current_dir + '/fixture/inventory/clusters/plugin_generator_scb.yaml', 'ssh',
                  'backend', '--ssh-dest-user', 'ec2-user', '-l', 'remote_user')

    assert re.match(r'ssh -F .+/ssh.config -t remote_user@172.16.0.1@scb\.example.com '
                    r'ssh ec2-user@172.16.0.2 -l remote_user', command['command'])

def test_ssh_scb_user_noscb():
    command = run(current_dir + '/fixture/inventory/clusters/plugin_generator_scb.yaml', 'ssh',
                  'bastion', '--noscb', '-l', 'remote_user')

    assert re.match('ssh -F .+/ssh.config bastion.host -l remote_user', command['command'])
    assert "scb.example.com" not in command['command']


if not PY3:
    def test_ssh_user_unicode_dash():
        with pytest.raises(UnicodeDecodeError):
            run(current_dir + '/fixture/inventory/clusters/plugin_generator.yaml', 'ssh',
                'bastion', '–l', 'remote_user')


def test_ssh_user_default():
    # we take the default system user
    command = run(current_dir + '/fixture/inventory/clusters/plugin_generator.yaml', 'ssh',
                       'bastion')

    current_user = os.environ.get("USER") or "root"
    assert '-l %s' % current_user in command['command']


def test_ssh_scb_user_default():
    # we take the default system user
    command = run(current_dir + '/fixture/inventory/clusters/plugin_generator_scb.yaml', 'ssh',
                  'bastion')

    current_user = os.environ.get("USER") or "root"
    assert '-l %s' % current_user in command['command']


def test_ssh_user_opsconfig():
    # we take the value from opsconfig, if present
    container = app(current_dir + '/fixture/inventory/clusters/plugin_generator.yaml',
                    'ssh', 'bastion')
    container.ops_config.config['ssh.user'] = 'test'

    command = container.run()

    assert '-l test' in command['command']


def test_ssh_user_opsconfig_override():
    # the value of the command line argument overrides .opsconfig.yaml

    container = app(current_dir + '/fixture/inventory/clusters/plugin_generator.yaml', 'ssh',
                       'bastion', '-l', 'ec2-user')

    container.ops_config.config['ssh.user'] = 'test'

    command = container.run()

    assert '-l ec2-user' in command['command']


def test_ssh_scb_user_opsconfig():
    # we take the value from opsconfig, if present
    container = app(current_dir + '/fixture/inventory/clusters/plugin_generator_scb.yaml',
                    'ssh',
                    'bastion')
    container.ops_config.config['ssh.user'] = 'test'

    command = container.run()

    assert '-l test' in command['command']


def test_ssh_scb_user_opsconfig_override():
    # the value of the command line argument overrides .opsconfig.yaml

    container = app(current_dir + '/fixture/inventory/clusters/plugin_generator_scb.yaml', 'ssh',
                    'bastion', '-l', 'ec2-user')

    container.ops_config.config['ssh.user'] = 'test'

    command = container.run()

    assert '-l ec2-user' in command['command']
