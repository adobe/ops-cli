# Release

1. Install: `pip install bump2version`
2. Bump version: `bump2version minor`
3. Push the release commit: `git push --follow-tags`
4. Wait for Travis to build at https://www.travis-ci.com/adobe/ops-cli  
  * This will publish a release to https://github.com/adobe/ops-cli/releases
  * Publish a new docker image version to https://hub.docker.com/r/adobe/ops-cli

