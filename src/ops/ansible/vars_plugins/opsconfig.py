#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import os

from ops.main import AppContainer
import logging

logger = logging.getLogger(__name__)

class VarsModule(object):

    """
    Loads local ops installation vars
    """

    def __init__(self, inventory):
        """ constructor """

        logger.debug("Running plugin: %s with cluster config %s" % (__file__, os.environ['OPS_CLUSTER_CONFIG']))

        app = AppContainer([os.environ['OPS_CLUSTER_CONFIG'], 'noop'])
        self.config = app.ops_config.config.copy()
        self.config.update({
                            'ops_package_dir': app.ops_config.package_dir,
                            'ops_ansible_tasks_dir': app.ops_config.package_dir + "/data/ansible/tasks"
                            })

    def run(self, host, vault_password=None):
        return self.config

    def get_host_vars(self, host, vault_password=None):
        """ Get host specific variables. """
        return self.config


    def get_group_vars(self, group, vault_password=None):
        """ Get group specific variables. """
        return self.config
