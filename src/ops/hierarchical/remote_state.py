#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

import boto3
import json


class S3TerraformRemoteStateRetriever:
    @staticmethod
    def get_s3_client(bucket_name, bucket_key, boto_profile):
        session = boto3.session.Session(profile_name=boto_profile)
        client = session.client('s3')
        try:
            bucket_object = client.get_object(Bucket=bucket_name, Key=bucket_key)["Body"].read()
            return json.loads(bucket_object)
        except (client.exceptions.NoSuchKey, client.exceptions.NoSuchBucket):
            return []

    def get_dynamic_data(self, remote_states):
        generated_data = {"outputs": {}}
        for state in remote_states:
            bucket_object = self.get_s3_client(state["s3_bucket"], state["s3_key"], state["aws_profile"])
            if "outputs" in bucket_object:
                generated_data["outputs"][state["name"]] = bucket_object["outputs"]
        return generated_data
