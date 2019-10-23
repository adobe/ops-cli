# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.


import logging
import os
import sys

from ops.cli.parser import SubParserConfig
from ops.hierarchical.composition_config_generator import CompositionConfigGenerator

logger = logging.getLogger(__name__)


class HelmfileParserConfig(SubParserConfig):
    def get_name(self):
        return 'helmfile'

    def get_help(self):
        return 'Wrap common helmfile tasks using hierarchical configuration support'

    def configure(self, parser):
        parser.add_argument(
            '--helmfile-path',
            type=str,
            default=None,
            help='Dir to where helmfile.yaml is located')
        return parser

    def get_epilog(self):
        return '''
        Examples:
            # Run helmfile sync
            ops data/env=dev/region=va6/project=ee/cluster=experiments/composition=helmfiles helmfile sync
            # Run helmfile sync for a single chart
            ops data/env=dev/region=va6/project=ee/cluster=experiments/composition=helmfiles helmfile --selector chart=nginx-controller sync
            # Run helmfile sync with concurrency flag
            ops data/env=dev/region=va6/project=ee/cluster=experiments/composition=helmfiles helmfile --selector chart=nginx-controller sync --concurrency=1
        '''


class HelmfileRunner(CompositionConfigGenerator, object):
    def __init__(self, ops_config, cluster_config_path, execute):
        super(HelmfileRunner, self).__init__(["helmfiles"])
        logging.basicConfig(level=logging.INFO)
        self.ops_config = ops_config
        self.cluster_config_path = cluster_config_path
        self.execute = execute

    def run(self, args, extra_args):
        config_path_prefix = os.path.join(self.cluster_config_path, '')
        default_helmfiles = '../ee-k8s-infra/compositions/helmfiles'
        args.helmfile_path = default_helmfiles if args.helmfile_path is None else os.path.join(
            args.helmfile_path, '')

        compositions = self.get_sorted_compositions(config_path_prefix)
        if len(compositions) == 0 or compositions[0] != "helmfiles":
            raise Exception(
                "Please provide the full path to composition=helmfiles")
        composition = compositions[0]
        conf_path = self.get_config_path_for_composition(
            config_path_prefix, composition)
        data = self.generate_helmfile_config(conf_path, args)
        self.setup_kube_config(data)

        command = self.get_helmfile_command(args, extra_args)
        return dict(command=command)

    def setup_kube_config(self, data):
        if data['helm']['global']['clusterType'] == 'eks':
            cluster_name = data['helm']['global']['fqdn']
            aws_profile = data['helm']['global']['aws']['name']
            region = data['helm']['global']['region']['location']
            file_location = self.generate_eks_kube_config(
                cluster_name, aws_profile, region)
            os.environ['KUBECONFIG'] = file_location
        else:
            logger.warning('currently only eks type clusters supported')
            sys.exit(1)

    def generate_eks_kube_config(self, cluster_name, aws_profile, region):
        file_location = self.get_tmp_file()
        cmd = "aws eks update-kubeconfig --name {} --profile {} --region {} --kubeconfig {}".format(cluster_name,
                                                                                                    aws_profile,
                                                                                                    region,
                                                                                                    file_location)
        return_code = self.execute(dict(command=cmd))
        if return_code != 0:
            raise Exception(
                "Unable to generate EKS kube config. Exit code was {}".format(return_code))
        return file_location

    @staticmethod
    def get_tmp_file():
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            return tmp_file.name

    def generate_helmfile_config(self, path, args):
        output_file = args.helmfile_path + "/hiera-generated.yaml"
        logger.info('Generating helmfiles config %s', output_file)


        try:
            excluded_keys = self.ops_config["compositions"]["excluded_config_keys"]["helmfile"]
        except KeyError:
            excluded_keys = []

        try:
            filtered_keys = self.ops_config["compositions"]["filtered_output_keys"]["helmfile"]
        except KeyError:
            filtered_keys = []

        return self.config_generator.generate_config(config_path=path,
                                                     filters=filtered_keys,
                                                     exclude_keys=excluded_keys,
                                                     output_format="yaml",
                                                     output_file=output_file,
                                                     print_data=True)

    def get_helmfile_command(self, args, extra_args):
        helmfile_args = ' '.join(extra_args)
        return "cd {helmfile_path} && helmfile {helmfile_args}".format(
            helmfile_path=args.helmfile_path,
            helmfile_args=helmfile_args)
