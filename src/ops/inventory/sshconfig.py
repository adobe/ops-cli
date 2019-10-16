# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from shutil import copy


class SshConfigGenerator(object):
    def __init__(self, package_dir):
        self.package_dir = package_dir

    def generate(self, directory):
        dest_ssh_config = directory + '/ssh_config'
        copy(self._get_ssh_config(), dest_ssh_config)

        return dest_ssh_config

    def _get_ssh_config(self):
        return self.package_dir + '/data/ssh/ssh.config'
