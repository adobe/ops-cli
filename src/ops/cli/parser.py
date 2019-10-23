# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import argparse

import sys

from six import PY3


class RootParser(object):
    def __init__(self, sub_parsers=None):
        """
        :type sub_parsers: list[SubParserConfig]
        """

        if sub_parsers is None:
            sub_parsers = []
        self.sub_parsers = sub_parsers

    def _get_parser(self):
        parser = argparse.ArgumentParser(
            description='Run commands against a cluster definition', prog='ops')
        parser.add_argument(
            'cluster_config_path',
            type=str,
            help='The cluster config path cluster.yaml')
        parser.add_argument('--root-dir', type=str, help='The root of the resource tree - '
                                                         'it can be an absolute path or relative to the current dir')
        parser.add_argument('--verbose', '-v', action='count',
                            help='Get more verbose output from commands')
        configure_common_arguments(parser)

        subparsers = parser.add_subparsers(dest='command')

        for subparser_conf in self.sub_parsers:
            subparser_instance = subparsers.add_parser(subparser_conf.get_name(),
                                                       help=subparser_conf.get_help(),
                                                       epilog=subparser_conf.get_epilog(),
                                                       formatter_class=subparser_conf.get_formatter())
            subparser_conf.configure(subparser_instance)

        subparsers.add_parser(
            'noop', help='used to initialize the full container for api usage')

        return parser

    @staticmethod
    def _check_args_for_unicode(args):
        if args is None:
            args = sys.argv

        try:
            for value in args:
                if not PY3 and isinstance(value, unicode):
                    # Python3 or some Python3 compatibility mode can make
                    # arguments to be unicode, not str
                    value.encode('utf-8').encode('utf-8')
                # Python 2 str, check if it can be represented in utf8
                elif isinstance(value, str):
                    value.encode('utf-8')
        except UnicodeDecodeError as e:
            print('Invalid character in argument "{0}", most likely an "en dash", replace it with normal dash -'.format(
                e.args[1]))
            raise

    def parse_args(self, args=None):
        RootParser._check_args_for_unicode(args)
        return self._get_parser().parse_args(args)

    def parse_known_args(self, args=None):
        RootParser._check_args_for_unicode(args)
        return self._get_parser().parse_known_args(args)


class SubParserConfig(object):
    def get_name(self):
        pass

    def configure(self, parser):
        pass

    def get_formatter(self):
        return argparse.RawDescriptionHelpFormatter

    def get_help(self):
        return ""

    def get_epilog(self):
        return ""


def configure_common_arguments(parser):
    parser.add_argument('-e', '--extra-vars', type=str, action='append', default=[],
                        help='Extra variables to use. Eg: -e ssh_user=ssh_user')

    return parser


def configure_common_ansible_args(parser):
    parser.add_argument('--ask-sudo-pass', action='store_true',
                        help='Ask sudo pass for commands that need sudo')
    parser.add_argument('--limit', type=str,
                        help='Limit run to a specific server subgroup. Eg: --limit newton-dcs')

    return parser
