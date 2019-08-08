# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from secret_resolvers import AggregatedSecretResolver
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

class SecretInjector(object):
    """
    Resolve secrets in the form:
    {{ssm.path(/aam/artifactory/grafana/password).aws_profile(aam-npe)}}
    or
    {{vault.kv2.path(ethos/k8s-ethos-config/thrash/aws/ClusterIngressTLS).field(Key)}}
    """

    def __init__(self):
        self.resolver = AggregatedSecretResolver()

    def is_interpolation(self, value):
        return value.startswith('{{') and value.endswith('}}')

    @lru_cache(maxsize=2048)
    def inject_secret(self, line):
        """
        Check if value is an interpolation and try to resolve it.
        Uses a cache, in order to not fetch same secret multiple times.
        """
        if not self.is_interpolation(line):
            return line

        # remove {{ and }}
        updated_line = line[2:-2]

        # parse each key/value (eg. path=my_pwd)
        parts = updated_line.split('.')
        if len(parts) <= 1:
            return line

        secret_type = parts[0]

        secret_params = {}
        for part in parts:
            if '(' not in part:
                secret_params[part] = None
            else:
                key = part.split('(')[0]
                value = part.split('(')[1].split(')')[0]
                secret_params[key] = value

        if self.resolver.supports(secret_type):
            return self.resolver.resolve(secret_type, secret_params)
        else:
            return line
