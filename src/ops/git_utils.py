# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import git
import logging
import os
import yaml

logger = logging.getLogger(__name__)


def setup_repo(repo_path, upstream_repo):
    """
    Ensure that the repo is present or clone it from upstream otherwise.
    """
    repo_path = os.path.expanduser(repo_path)

    try:
        git.Repo(repo_path, search_parent_directories=True)
    except git.NoSuchPathError:
        logger.warning(
            "Repo '%s' not found. Cloning from upstream '%s'", repo_path, upstream_repo
        )
        git.Repo.clone_from(upstream_repo, repo_path)


def checkout_repo(repo_path, config_path, get_version):
    with open(os.path.expanduser(config_path)) as f:
        conf = yaml.load(f, Loader=yaml.SafeLoader)

    version = get_version(conf)
    repo = git.Repo(repo_path, search_parent_directories=True)

    repo.git.fetch()
    repo.git.checkout(version)

    logger.info(
        "Checked out repo '%s' to version '%s'",
        repo.git.rev_parse("--show-toplevel"),
        version,
    )
