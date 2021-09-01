# Release

1. Install: `pip install bump2version`
2. Bump version: `bump2version patch --new-version=2.0.4`
3. Push the release commit: `git push --follow-tags`
4. Wait for GH Actions to release packages: https://github.com/adobe/ops-cli/actions/workflows/release.yml/
  * This will publish the pypi package to https://pypi.org/project/ops-cli/
  * Publish a new docker image version to https://github.com/adobe/ops-cli/pkgs/container/ops-cli
5. Open a new `dev` cycle: e.g `bump2version patch --new-version=2.0.5dev`
