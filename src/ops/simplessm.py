# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

#!/usr/bin/env python

from botocore.exceptions import ClientError
import boto3
import os


class SimpleSSM(object):
    def __init__(self, aws_profile, region_name):
        self.initial_aws_profile = os.getenv('AWS_PROFILE', None)
        self.aws_profile = aws_profile
        self.region_name = region_name

    def get(self, key):
        client = self.get_ssm_client()
        try:
            return client.get_parameter(Name=key, WithDecryption=True).get(
                "Parameter").get("Value")
        except ClientError as e:
            raise Exception(
                'Error while trying to read SSM value for key: %s - %s' %
                (key, e.response['Error']['Code']))
        finally:
            self.release_ssm_client()

    def get_ssm_client(self):
        os.environ['AWS_PROFILE'] = self.aws_profile
        return boto3.client('ssm', region_name=self.region_name)

    def release_ssm_client(self):
        if self.initial_aws_profile is None:
            del os.environ['AWS_PROFILE']
        else:
            os.environ['AWS_PROFILE'] = self.initial_aws_profile
