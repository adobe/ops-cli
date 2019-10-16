# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import pkg_resources
import re
from distutils.version import StrictVersion
from subprocess import call, Popen, PIPE

from six import PY3

from .cli import display


def validate_ops_version(min_ops_version):
    current_ops_version = [
        x.version for x in pkg_resources.working_set if x.project_name == "ops-cli"][0]
    if StrictVersion(current_ops_version) < StrictVersion(min_ops_version):
        raise Exception("The current ops version {0} is lower than the minimum required version {1}. "
                        "Please upgrade by following the instructions seen here: "
                        "https://github.com/adobe/ops-cli#installing".format(current_ops_version, min_ops_version))


class Executor(object):
    """ All cli commands usually return a dict(command=...) that will be executed by this handler"""

    def __call__(self, result, pass_trough=True, cwd=None):
        try:
            return self._execute(result, pass_trough, cwd)
        except Exception as ex:
            display(str(ex) if PY3 else ex.message, stderr=True, color='red')
            display(
                '------- TRACEBACK ----------',
                stderr=True,
                color='dark gray')
            import traceback
            traceback.print_exc()
            display(
                '------ END TRACEBACK -------',
                stderr=True,
                color='dark gray')

    def _execute(self, result, pass_trough=True, cwd=None):
        if not result or not isinstance(result, dict):
            return

        if 'command' in result:
            shell_command = result['command']
            display(
                "%s" %
                self.shadow_credentials(shell_command),
                stderr=True,
                color='yellow')
            if pass_trough:
                exit_code = call(shell_command, shell=True, cwd=cwd)
            else:
                p = Popen(
                    shell_command,
                    shell=True,
                    stdout=PIPE,
                    stderr=PIPE,
                    cwd=cwd)
                output, errors = p.communicate()
                display(str(output))
                if errors:
                    display(
                        "%s" %
                        self.shadow_credentials(errors),
                        stderr=True,
                        color='red')
                exit_code = p.returncode

        if 'post_actions' in result:
            for callback in result['post_actions']:
                callback()

        return exit_code

    def shadow_credentials(self, cmd):
        cmd = re.sub(r"secret_key=.{20}", "secret_key=****", cmd)
        cmd = re.sub(r'access_key=.{10}', 'access_key=****', cmd)

        return cmd


class OpsException(Exception):
    pass
