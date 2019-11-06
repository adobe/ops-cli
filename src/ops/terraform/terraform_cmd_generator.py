# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import os
import re
import shutil
import logging

from jinja2 import FileSystemLoader
from subprocess import Popen, PIPE
from ops.cli import err, display


class TerraformCommandGenerator(object):
    def __init__(self, root_dir, cluster_config,
                 inventory_generator, ops_config, template):
        self.cluster_config = cluster_config
        self.root_dir = root_dir
        self.inventory_generator = inventory_generator
        self.ops_config = ops_config
        self.template = template

    def generate(self, args):

        self.selected_terraform_path = args.path_name
        self.set_current_working_dir()
        current_terraform_version = self.check_terraform_version()
        config = self.cluster_config

        current_terraform_version_major = int(
            current_terraform_version.split('.')[1])
        if 'enable_consul_remote_state' in config['terraform']:
            terraform_remote_state = config['terraform']['enable_consul_remote_state']
        elif config['terraform'].get('state', {'type': None}).get('type') == 's3':
            terraform_remote_state = 'true'
        else:
            terraform_remote_state = 'false'

        terraform_config = config.get('terraform', {})
        terraform_path = self.get_terraform_path()
        generate_module_templates = False

        plan_variables = terraform_config.get('vars', {})
        if not config['cluster'].startswith("auto_generated"):
            plan_variables['cluster'] = config['cluster']
        if self.cluster_config.has_ssh_keys:
            plan_variables['has_ssh_keys'] = True
            plan_variables['cluster_ssh_pubkey_file'] = self.cluster_config.cluster_ssh_pubkey_file
            plan_variables['cluster_ssh_prvkey_file'] = self.cluster_config.cluster_ssh_prvkey_file
        if terraform_config.get('boto_profile'):
            self.add_profile_vars(
                plan_variables,
                terraform_config.get('boto_profile'))

        vars = ''
        for key, val in plan_variables.items():
            vars += " -var '%s=%s' " % (key, val)

        state_file = 'terraform.{cluster}.tfstate'.format(
            cluster=config['cluster'])
        plan_file = 'terraform.{cluster}.plan'.format(
            cluster=config['cluster'])
        landscape = ''

        if current_terraform_version_major >= 9:
            if args.force_copy:
                terraform_init_command = 'terraform init -force-copy && '
            else:
                terraform_init_command = 'terraform init && '
            # regarding state location we give priority to the cli parameter
            if args.state_location == 'remote':
                state_argument = ''
                state_out_argument = ''
            elif args.state_location == 'local':
                state_argument = "-state={state_file}".format(
                    state_file=state_file
                )
                state_out_argument = "-state-out={state_file}".format(
                    state_file=state_file
                )
            else:
                # no cli parameter, decide based on config file
                if terraform_remote_state == 'true':
                    state_argument = ''
                    state_out_argument = ''
                else:
                    state_argument = "-state={state_file}".format(
                        state_file=state_file
                    )
                    state_out_argument = "-state-out={state_file}".format(
                        state_file=state_file
                    )
        else:
            state_argument = "-state={state_file}".format(
                state_file=state_file
            )
            state_out_argument = "-state-out={state_file}".format(
                state_file=state_file
            )
            terraform_init_command = ''

        remove_local_cache = 'rm -rf .terraform && ' if \
            self.ops_config['terraform.remove_local_cache'] else ''

        if args.subcommand == 'template':
            if args.template_location:
                self.copy_static_files(args.template_location, terraform_path)
                self.write_module_templates(args.template_location)
                self.write_var_file(
                    os.path.join(
                        args.template_location,
                        terraform_path),
                    plan_variables)
            else:
                for original, fname, contents in self.get_templated_files():
                    display("# %s -> %s" % (original, fname), color="green")
                    display("# --------------", color="green")
                    display(contents)
            return

        if "variables_file" in config['terraform']:
            variables_file = ' -var-file="{}" '.format(
                config['terraform']["variables_file"])
        else:
            variables_file = ' '

        auto_approve = '-auto-approve' if args.auto_approve else ''

        if args.subcommand == 'plan':
            generate_module_templates = True
            terraform_refresh_command = ''
            if args.do_refresh:
                terraform_refresh_command = "terraform refresh" \
                                            "{variables_file}" \
                                            " -input=false {vars} {state_argument} && ".format(vars=vars,
                                                                                               state_argument=state_argument,
                                                                                               variables_file=variables_file)

            if self.ops_config['terraform.landscape'] and not args.raw_plan_output:
                landscape = '| landscape'

            cmd = "cd {terraform_path} && " \
                  "{remove_local_cache}" \
                  "terraform get -update && " \
                  "{terraform_init_command}" \
                  "{terraform_refresh_command}" \
                  "terraform plan " \
                  "{variables_file}" \
                  "-out={plan_file} -refresh=false -input=false {vars} {state_argument}".format(
                      terraform_path=terraform_path,
                      terraform_init_command=terraform_init_command,
                      vars=vars,
                      state_argument=state_argument,
                      plan_file=plan_file,
                      terraform_refresh_command=terraform_refresh_command,
                      remove_local_cache=remove_local_cache,
                      variables_file=variables_file
                  )

        elif args.subcommand == 'apply':
            # the following is to have auxiliary rendered/templated files like cloudinit.yaml
            # that also needs templating. Without it, plan works but apply does not for this kind of files
            # todo maybe this deserves a better implementation later
            generate_module_templates = True

            self.inventory_generator.clear_cache()
            if args.skip_plan:
                # Run Terraform apply without running a plan first
                cmd = "cd {terraform_path} && " \
                      "{remove_local_cache}" \
                      "{terraform_init_command}" \
                      "rm -f {plan_file} && terraform apply {vars}" \
                      "-refresh=true {state_argument} {variables_file} {auto_approve}".format(
                          plan_file=plan_file,
                          state_argument=state_argument,
                          remove_local_cache=remove_local_cache,
                          terraform_init_command=terraform_init_command,
                          terraform_path=terraform_path,
                          vars=vars,
                          variables_file=variables_file,
                          auto_approve=auto_approve
                      )
            else:
                cmd = "cd {terraform_path} && " \
                      "terraform apply " \
                      "-refresh=true {state_out_argument} {plan_file}; code=$?; rm -f {plan_file}; exit $code".format(
                          plan_file=plan_file,
                          state_out_argument=state_out_argument,
                          terraform_path=terraform_path,
                          vars=vars,
                          variables_file=variables_file
                      )

        elif args.subcommand == 'destroy':
            generate_module_templates = True
            cmd = "cd {terraform_path} && " \
                  "{remove_local_cache}" \
                  "{terraform_init_command}" \
                  "terraform plan -destroy " \
                  "-refresh=true {vars} {variables_file} {state_argument} && " \
                  "terraform destroy {vars} {variables_file} {state_argument} -refresh=true {auto_approve}".format(
                      terraform_path=terraform_path,
                      variables_file=variables_file,
                      vars=vars,
                      state_argument=state_argument,
                      terraform_init_command=terraform_init_command,
                      remove_local_cache=remove_local_cache,
                      auto_approve=auto_approve
                  )
        elif args.subcommand == 'output':
            cmd = "cd {terraform_path} && " \
                  "terraform output {state_argument} {output}".format(
                      terraform_path=terraform_path,
                      output=args.var,
                      state_argument=state_argument
                  )
        elif args.subcommand == 'refresh':
            generate_module_templates = True
            cmd = "cd {terraform_path} && " \
                  "terraform get -update && " \
                  "terraform refresh {variables_file} {state_argument} {vars}".format(
                      terraform_path=terraform_path,
                      vars=vars,
                      variables_file=variables_file,
                      state_argument=state_argument
                  )
        elif args.subcommand == 'taint' or args.subcommand == 'untaint':
            cmd = "cd {terraform_path} && " \
                  "{remove_local_cache}" \
                  "{terraform_init_command}" \
                  "terraform {command} {state_argument} -module={module} {resource}".format(
                      command=args.subcommand,
                      terraform_path=terraform_path,
                      resource=args.resource,
                      module=args.module,
                      state_argument=state_argument,
                      terraform_init_command=terraform_init_command,
                      remove_local_cache=remove_local_cache
                  )
        elif args.subcommand == 'show':
            if args.plan:
                state = plan_file
            else:
                state = state_file

            cmd = "cd {terraform_path} && " \
                  "terraform show {state}".format(
                      terraform_path=terraform_path,
                      state=state
                  )
        elif args.subcommand == 'import':
            generate_module_templates = True
            cmd = "cd {terraform_path} && " \
                  "terraform import {state_argument} {vars} module.{module}.{resource} {name}".format(
                      command=args.subcommand,
                      terraform_path=terraform_path,
                      resource=args.resource,
                      module=args.module,
                      name=args.name,
                      state_argument=state_argument,
                      vars=vars,
                  )
        elif args.subcommand == 'console':
            generate_module_templates = True
            cmd = "cd {terraform_path} && " \
                  "terraform {command} {state_argument} {vars}".format(
                      command=args.subcommand,
                      terraform_path=terraform_path,
                      state_argument=state_argument,
                      vars=vars,
                  )
        elif args.subcommand == 'validate':
            generate_module_templates = True
            cmd = "cd {terraform_path} && " \
                  "{remove_local_cache}" \
                  "{terraform_init_command} " \
                  "terraform {command} {vars} {variables_file}".format(
                      command=args.subcommand,
                      remove_local_cache=remove_local_cache,
                      terraform_init_command=terraform_init_command,
                      terraform_path=terraform_path,
                      vars=vars,
                      variables_file=variables_file
                  )
        elif args.subcommand is not None:
            # Examples:
            #  - command = "state push errored.tfstate"
            #  - command = "force-unlock <LOCK_ID>"
            generate_module_templates = True
            cmd = "cd {terraform_path} && " \
                  "{remove_local_cache}" \
                  "{terraform_init_command} " \
                  "terraform {command}".format(
                      command=args.subcommand,
                      remove_local_cache=remove_local_cache,
                      terraform_init_command=terraform_init_command,
                      terraform_path=terraform_path,
                  )
        else:
            display(
                'Terraform subcommand \'%s\' not found' %
                args.subcommand, color='red')
            return

        if generate_module_templates:
            self.write_module_templates()
            post_actions = [self.remove_module_template]
        else:
            post_actions = []

        # pass on the terraform args to the terraform command line
        cmd = ' '.join([cmd] + args.terraform_args + [landscape])

        return dict(
            command=cmd,
            post_actions=post_actions
        )

    def add_profile_vars(self, plan_variables, profile_name):
        plan_variables['profile'] = '"%s"' % profile_name

        home_dir = os.environ.get('HOME')
        plan_variables['shared_credentials_file'] = '"{}/.aws/credentials"'.format(
            home_dir)
        # plan_variables['access_key'] = '"%s"' % aws.access_key(profile_name)
        # plan_variables['secret_key'] = '"%s"' % aws.secret_key(profile_name)

    def get_terraform_path(self):
        if 'path' in self.cluster_config['terraform']:
            return self.cluster_config['terraform']['path']

        if 'paths' not in self.cluster_config['terraform']:
            raise Exception(
                "Could not find 'terraform.path' / 'terraform.paths' in the cluster configuration")

        paths = self.cluster_config['terraform']['paths']
        selected = self.selected_terraform_path
        if selected is None:
            raise Exception(
                'You need to specify which path you want to use with --path-name. Options are: %s ' % paths.keys())

        try:
            return paths[selected]
        except KeyError:
            raise Exception(
                "Could not find path '%s' in 'terraform.paths'. Options are: %s" %
                (selected, paths.keys()))

    def get_terraform_src_paths(self):
        return [self.get_terraform_path()]

    def check_terraform_version(self):
        expected_version = self.ops_config['terraform.version']

        try:
            execution = Popen(['terraform', '--version'],
                              stdin=PIPE, stdout=PIPE, stderr=PIPE)
        except Exception as e:
            logging.exception(
                "Terraform does not appear to be installed, "
                "please ensure terraform is in your PATH"
            )
            exit(1)
        current_version, execution_error = execution.communicate()
        current_version = current_version.decode(
            'utf-8').replace('Terraform ', '').split('\n', 1)[0]
        if expected_version == 'latest':
            return current_version

        if current_version != expected_version and execution.returncode == 0:
            raise Exception("Terraform should be %s, but you have %s. Please change your version."\
                            % (expected_version, current_version)
            )

        return current_version

    def get_templated_files(self):
        for path in self.get_terraform_src_paths():
            for source, dest, content in self.template_files(path):
                yield source, dest, content

    def copy_static_files(self, path, terraform_path):
        shutil.copytree(
            os.path.join(
                self.root_dir, terraform_path), os.path.join(
                path, terraform_path))
        shutil.copytree(
            os.path.join(
                self.root_dir, 'modules'), os.path.join(
                path, 'modules'))

    def write_var_file(self, path, variables):
        fname = os.path.join(path, 'ops.auto.tfvars')
        with open(fname, 'wb') as f:
            for key, val in variables.items():
                if val[0] != '"':
                    val = '"{}"'.format(val)
                f.write("{key} = {val}\n".format(key=key, val=val))

    def write_module_templates(self, path=''):
        for original, fname, result in self.get_templated_files():
            if path:
                fname = os.path.join(path, fname)
                folder = os.path.dirname(fname)
                if not os.path.exists(folder):
                    os.makedirs(folder)
            with open(fname, 'wb') as f:
                f.write(result.encode('utf8'))

    def remove_module_template(self):
        filenames = set()
        for source, dest, content in self.get_templated_files():
            filenames.add(dest)
        for filename in filenames:
            try:
                os.remove(filename)
            except BaseException:
                err('Could not remove file %s' % filename)

    def get_terraform_module_paths(self, rendered):
        """ Return list of relative module paths that are included in a terraform
            config file """

        return re.findall(r'source\s*=\s*"(.+?)"', rendered)

    def template_files(self, path):
        result = []
        terraform_file_contents = self.get_terraform_files(path)

        for source in self.list_jinja_templates(path):
            dest = source.replace(".jinja2", "")
            config_all = self.cluster_config.all()
            # Allow access to configuration values in Jinja2. Replace '.' with
            # '_' to make them valid variable names
            config_all['opsconfig'] = {
                k.replace(
                    '.',
                    '_'): v for k,
                v in self.ops_config.all().items()}
            config_all['selected_terraform_path'] = self.selected_terraform_path
            if config_all.get('terraform', {}).get('boto_profile'):
                self.add_profile_vars(
                    config_all, config_all['terraform']['boto_profile'])
            rendered = self.template.render(source, config_all)

            terraform_file_contents.append(rendered)

            result.append((source, dest, rendered))

        # search for module references in all terraform files in this path,
        # including rendered templates
        for discovered_module in self.find_referenced_modules(
                path, terraform_file_contents):
            result.extend(self.template_files(discovered_module))

        return result

    def find_referenced_modules(self, base_path, terraform_files):
        # look for terraform module references in this path
        ret = set()

        for rendered in terraform_files:
            for relative_module_path in self.get_terraform_module_paths(
                    rendered):
                new_path = os.path.normpath(
                    base_path + '/' + relative_module_path)
                ret.add(new_path)

        return ret

    def list_files(self, path, extension):
        template_paths = []
        loader = FileSystemLoader(path)
        for fname in loader.list_templates():
            name, ext = os.path.splitext(fname)
            template_path = path + '/' + fname
            # Do not go into terraform community provided modules
            if ext == extension and '.terraform' not in template_path:
                template_paths.append(template_path)

        return template_paths

    def get_terraform_files(self, path):
        ret = []
        for fname in self.list_files(path, '.tf'):
            with open(fname) as f:
                ret.append(f.read())

        return ret

    def list_jinja_templates(self, path):
        return self.list_files(path, '.jinja2')

    def set_current_working_dir(self):
        os.chdir(self.root_dir)
