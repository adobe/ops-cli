#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import os
from argparse import Namespace

from ops.opsconfig import OpsConfig

current_dir = os.path.dirname(__file__)


def test_configuration_overrides():
    cfg = OpsConfig(Namespace(cluster_config_path=current_dir + '/fixture/clusters/prod/us-east-1/test.yaml'), '')

    assert 'vars.random' not in cfg
    assert cfg['terraform.version'] == 'override_version'
    assert cfg['vars.region'] == 'us-east-1'
    assert cfg['vars.env'] == 'prod'

    cfg = OpsConfig(Namespace(cluster_config_path=current_dir + '/fixture/clusters/dev/us-west-1/test.yaml'), '')
    assert cfg['terraform.version'] == 'override_version'
    assert cfg['vars.region'] == 'us-west-1'
    assert cfg['vars.env'] == 'dev'
