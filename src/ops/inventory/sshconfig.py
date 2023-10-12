# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import os
import socketserver
from shutil import copy
from pathlib import Path
from ansible.playbook.play import display


class SshConfigGenerator(object):
    SSH_CONFIG_FILE = "ssh.config"
    SSH_SCB_PROXY_TPL_FILE = "ssh.scb.proxy.config.tpl"

    def __init__(self, package_dir):
        self.package_dir = package_dir
        self.ssh_data_dir = self.package_dir + '/data/ssh'
        self.ssh_config_files = [self.SSH_CONFIG_FILE, self.SSH_SCB_PROXY_TPL_FILE]

    def generate(self, directory):
        dest_ssh_config = {}
        for index, ssh_config in enumerate(self._get_ssh_config()):
            ssh_config_file = self.ssh_config_files[index]
            dest_ssh_config[ssh_config_file] = f"{directory}/{ssh_config_file.replace('.', '_')}"
            copy(ssh_config, dest_ssh_config[ssh_config_file])
        return dest_ssh_config

    def _get_ssh_config(self):
        return [f"{self.ssh_data_dir}/{ssh_config_file}"
                for ssh_config_file in self.ssh_config_files]

    @staticmethod
    def get_ssh_config_path(cluster_config, ssh_config_paths, use_scb):
        scb_settings = cluster_config.get('scb', {})
        scb_enabled = scb_settings.get('enabled') and use_scb
        if scb_enabled:
            ssh_config_tpl_path = ssh_config_paths.get(SshConfigGenerator.SSH_SCB_PROXY_TPL_FILE)
            scb_proxy_port = SshConfigGenerator.get_ssh_scb_proxy_port(ssh_config_tpl_path)
            ssh_config_path = SshConfigGenerator.generate_ssh_scb_config(ssh_config_tpl_path,
                                                                         scb_proxy_port)
            display.display(f"Connecting via scb proxy at 127.0.0.1:{scb_proxy_port}.\n"
                            f"This proxy should have already been started and running "
                            f"in a different terminal window.\n"
                            f"If there are connection issues double check that "
                            f"the proxy is running.",
                            color='blue',
                            stderr=True)
        else:
            ssh_config_path = ssh_config_paths.get(SshConfigGenerator.SSH_CONFIG_FILE)
        return ssh_config_path

    @staticmethod
    def generate_ssh_scb_proxy_port(ssh_config_path, auto_scb_port, scb_config_port):
        ssh_config_port_path = f"{ssh_config_path}/ssh_scb_proxy_config_port"
        if auto_scb_port:
            with socketserver.TCPServer(("localhost", 0), None) as s:
                generated_port = s.server_address[1]
            display.display(f"Using auto generated port {generated_port} for scb proxy port",
                            color='blue',
                            stderr=True)
        else:
            generated_port = scb_config_port
            display.display(f"Using port {generated_port} from cluster config for scb proxy port",
                            color='blue',
                            stderr=True)

        with open(ssh_config_port_path, 'w') as f:
            f.write(str(generated_port))
            os.fchmod(f.fileno(), 0o644)

        return generated_port


    @staticmethod
    def get_ssh_scb_proxy_port(ssh_config_path):
        ssh_port_path = ssh_config_path.replace("_tpl", "_port")
        ssh_scb_proxy_port = Path(ssh_port_path).read_text()
        return ssh_scb_proxy_port

    @staticmethod
    def generate_ssh_scb_config(ssh_config_tpl_path, scb_proxy_port):
        ssh_config_template = Path(ssh_config_tpl_path).read_text()
        ssh_config_content = ssh_config_template.format(
            scb_proxy_port=scb_proxy_port
        )
        ssh_config_path = ssh_config_tpl_path.removesuffix("_tpl")
        with open(ssh_config_path, 'w') as f:
            f.write(ssh_config_content)
            os.fchmod(f.fileno(), 0o644)

        return ssh_config_path
