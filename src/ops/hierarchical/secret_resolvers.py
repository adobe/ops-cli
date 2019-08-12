#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

from ops.simplessm import SimpleSSM

class SecretResolver:
    def supports(self, secret_type):
        return False
    
    def resolve(self, secret_type, secret_params):
        return None


class SSMSecretResolver(SecretResolver):
    def __init__(self, default_aws_profile=None):
        self.default_aws_profile = default_aws_profile

    def supports(self, secret_type):
        return secret_type == "ssm"

    def resolve(self, secret_type, secret_params):
        aws_profile = secret_params.get("aws_profile", self.default_aws_profile)
        if not aws_profile:
            raise Exception("Could not find the aws_profile in the secret params: {}".format(secret_params))

        path = self.get_param_or_exception("path", secret_params)
        region_name = secret_params.get("region_name", "us-east-1")
        ssm = SimpleSSM(aws_profile, region_name)
        return ssm.get(path)

    def get_param_or_exception(self, key, params):
        if key not in params:
            raise Exception("Could not find required key '{}' in the secret params: {}".format(key, params))
        return params[key]


# TODO - vault resolver
class VaultSecretResolver(SecretResolver):
    def supports(self, secret_type):
        return False

    def resolve(self, secret_type, secret_params):
        return None


class AggregatedSecretResolver(SecretResolver):

    def __init__(self, default_aws_profile=None):
        self.secret_resolvers = (SSMSecretResolver(default_aws_profile), VaultSecretResolver())

    def supports(self, secret_type):
        return any([resolver.supports(secret_type) for resolver in self.secret_resolvers])
    
    def resolve(self, secret_type, secret_params):
        for resolver in self.secret_resolvers:
            if resolver.supports(secret_type):
                return resolver.resolve(secret_type, secret_params)

        raise Exception("Could not resolve secret type '{}' with params {}".format(secret_type, secret_params))
