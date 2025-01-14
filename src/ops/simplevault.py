# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

#!/usr/bin/env python

'''
Very simple secrets management that can be used to
- write vault items (with the SimpleVault.put())
- read vault items (with the SimpleVault.get())
- generate a password (with ManagedVaultSecret)
- manage the password in vault with  ManagedVaultSecret
  (ex: generate it only if it's not already there)
- it will also attempt login, if it will be required
'''

import os
import hvac
import getpass
from .cli import display
from six import iteritems, string_types

MAX_LDAP_ATTEMPTS = 3


class SimpleVault(object):
    p_vault_conn = None
    # persistent vault connection

    def __init__(
            self, vault_user=None, vault_addr=None, vault_token=None, namespace=None,
            mount_point=None, persistent_session=True, auto_prompt=True):

        self.vault_addr = vault_addr or os.getenv(
            'VAULT_ADDR', None) or "http://localhost:8200"
        # Actually maybe we should reconsider having a default vault addr.
        # How often we will create infrastructures
        # with vault running on the provisioner's machine ?
        self.vault_token = vault_token or os.getenv(
            'VAULT_TOKEN', None) or self.try_reading_token_file()
        self.vault_user = vault_user or os.getenv(
            'VAULT_USER', None) or getpass.getuser()
        self.mount_point = mount_point
        self.namespace = namespace
        self.ldap_attempts = 0

        if persistent_session:
            if SimpleVault.p_vault_conn:
                self.vault_conn = SimpleVault.p_vault_conn
            else:
                self.vault_conn = hvac.Client(
                    url=self.vault_addr,
                    namespace=self.namespace,
                    token=self.vault_token)

        auth_methods = {
            'ldap': self.auth_with_ldap,
            'okta': self.auth_with_okta
        }
        auth_method = os.getenv('OPS_VAULT_AUTH_METHOD', 'okta')

        while not self.vault_conn.is_authenticated() and auto_prompt:
            display("VAULT-LIB: Not authenticated to vault '%s'" %
                    self.vault_addr, stderr=True, color='red')
            display("Note: the default Vault username (%s) can be overwritten with VAULT_USER"
                     % self.vault_user, stderr=True,
                    color='yellow')
            display(
                "      or to pass a token directly use VAULT_TOKEN",
                stderr=True,
                color='yellow')

            auth_method_func = auth_methods.get(auth_method)
            if not auth_method_func:
                raise ValueError(f"Unsupported authentication method: {auth_method}")
            auth_method_func()

    @staticmethod
    def try_reading_token_file():
        ret = None
        try:
            ret = open(
                os.path.expanduser('~/.vault-token'),
                "r").read().strip()
        except Exception:
            ret = None
            pass
        return ret

    @staticmethod
    def write_token(token=None):
        try:
            if token:
                open(
                    os.path.expanduser('~/.vault-token'),
                    "w").write(
                    token.strip())
        except Exception:
            display(
                "Warning: could not persist token to ~/.vault-token",
                stderr=False,
                color='yellow')
            pass

    def auth_with_ldap(self):
        # LDAP authentication logic
        try:
            self.ldap_attempts += 1
            ldap_password = getpass.getpass(
                prompt='LDAP password for %s for server %s: ' %
                       (self.vault_user, self.vault_addr))
            auth_response = self.vault_conn.auth.ldap.login(
                username=self.vault_user, password=ldap_password)
            self.vault_conn.is_authenticated()
            self.vault_token = auth_response['auth']['client_token']
            self.write_token(self.vault_token)
        except Exception as e:
            if self.ldap_attempts >= MAX_LDAP_ATTEMPTS:
                display(
                    "FAILED authentication {} times".format(
                        self.ldap_attempts), color='red')
                raise e
            else:
                pass

    def auth_with_okta(self):
        try:
            okta_password = getpass.getpass(
                prompt=f"Okta password for {self.vault_user}: ")

            display("Authenticating with Okta...", color='yellow')
            auth_response = self.vault_conn.auth.okta.login(
                username=self.vault_user, password=okta_password)

            # Check the MFA requirement
            auth_data = auth_response.get("auth", {})
            mfa_requirement = auth_data.get("mfa_requirement")

            mfa_request_id = mfa_requirement.get("mfa_request_id")
            mfa_constraints = mfa_requirement.get("mfa_constraints", {})

            okta_factors = mfa_constraints.get("okta", {}).get("any", [])
            mfa_factor_id = okta_factors[0].get("id")

            # Create the MFA validation payload
            mfa_payload = {
                "mfa_request_id": mfa_request_id,
                "mfa_payload": {
                    mfa_factor_id: []  # No MFA factor specific data required
                }
            }

            # Make the MFA validation request
            display("Performing Okta MFA validation. Check notification...", color='yellow')
            mfa_response = self.vault_conn.adapter.post(
                "/v1/sys/mfa/validate",
                json=mfa_payload,
            )

            # Update token if provided after MFA
            self.vault_token = self.vault_conn.adapter.get_login_token(mfa_response)
            self.vault_conn.token = self.vault_token
            self.write_token(self.vault_token)
            if self.vault_conn.is_authenticated():
                display("Okta MFA validation successful, token obtained.", color='green')
            else:
                display("Okta MFA validation failed."
                        "Please obtain a token manually (vault cli) and run ops again.",
                        stderr=True, color='red')
                exit(1)

        except Exception as e:
            display(f"An error occurred during Okta authentication: {e}\n"
                    "Please obtain a token manually (vault cli) and run ops again.",
                    stderr=True, color='red')
            exit(1)

    def get(self, path, key='value', wrap_ttl=None,
            default=None, fetch_all=False, raw=False):
        if raw:
            fetch_all = True
        if fetch_all:
            key = None
        raw_data = self.vault_conn.secrets.kv.v2.read_secret_version(
            path=path, mount_point=self.mount_point)
        # move this check earlier, and, if true, return immediately
        if raw:
            return raw_data
        data = raw_data.get('data')
        if isinstance(data, dict):
            if not fetch_all:
                if key:
                    # the actual secret k v pairs are nested under another
                    # dictionary key "data"
                    return data.get("data").get(key, default)
                else:
                    raise('VAULT-LIB: either key or fetch_all should be set!')

    def check(self, path, key):
        # somewhat boilerplate method that returns a boolean whether the provided secret exists
        # and if it has the desired key, with a non-empty value
        try:
            raw_data = self.vault_conn.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self.mount_point)
            if key not in raw_data["data"]["data"]:
                return False
            if raw_data["data"]["data"][key] is None:
                return False
        except Exception as e:
            # if the provided secret path doesn't exist, return false
            return False
        return True

    def put(self, path, value, lease=None, wrap_ttl=None):
        payload = {}
        if isinstance(value, (string_types, int, float, bool)):
            payload['value'] = str(value)
        elif isinstance(value, dict):
            for k, v in iteritems(value):
                payload[k] = str(v)
        else:
            raise Exception('Unsupported data type for secret payload')
        self.vault_conn.secrets.kv.v2.create_or_update_secret(
            path=path, secret=payload, mount_point=self.mount_point)

    def is_authenticated(self):
        return self.vault_conn.is_authenticated()


class ManagedVaultSecret(object):
    p_sv = None
    # Persistent SimpleVault accessory object

    def __init__(
            self, path, key='value', policy={}, vault_user=None, vault_addr=None,
            vault_token=None, namespace=None, mount_point=None, auto_prompt=True):

        self.__DEFAULT_POLICY__ = {
            'engine': 'passgen',
            'length': 24
        }
        self.current_data = {}
        self.already_initialized = False
        self.actual_policy = self.__DEFAULT_POLICY__.copy()
        self.key = key
        self.mount_point = mount_point
        self.namespace = namespace
        if isinstance(policy, int):
            self.actual_policy.update({'length': policy})
        elif isinstance(policy, dict):
            self.actual_policy.update(policy)
        else:
            raise Exception(
                "Incorrect policy specified. Use a number if unsure.")
        if path:
            self.vault_path = path
        else:
            raise Exception("Invalid path for secret")
        self.policy = policy
        if ManagedVaultSecret.p_sv and ManagedVaultSecret.p_sv.is_authenticated():
            self.sv = ManagedVaultSecret.p_sv
        else:
            try:
                self.sv = SimpleVault(
                    vault_user=None, vault_addr=None, vault_token=None, auto_prompt=True,
                    namespace=self.namespace, mount_point=self.mount_point)
                ManagedVaultSecret.p_sv = self.sv
            except Exception as e:
                display(
                    'MANAGED-SECRET: could not obtain a proper'
                    ' Vault connection.\n{}'.format(e.message)
                )
                raise e
        try:
            self.current_data = self.sv.get(path=path, fetch_all=True)
        except Exception as e:
            display('MANAGED-SECRET: could not confirm if secret at path {} does or not already exist. '
                    'Exception was:\n{}'.format(path, e.message))
            raise e
        if self.current_data.get(key):
            # something exists on that path, we assume the secret already
            # exists and do nothing more
            pass
        else:
            # secret does not exist, we will generate it right now according to
            # the desired policy
            generator_args = self.actual_policy.copy()
            engine = generator_args.pop('engine', None)
            if self.actual_policy['engine'] == 'passgen':
                try:
                    import passgen
                except ImportError as e:
                    display(
                        'MANAGED-SECRET: You need passgen python module '
                        'in order to use the passgen engine.'
                    )
                    raise e
                try:
                    # generating and storing the new secret
                    self.new_data = self.current_data.copy()
                    self.new_data[key] = passgen.passgen(**generator_args)
                    self.sv.put(path, self.new_data)
                    self.already_initialized = True
                    self.current_data = self.new_data
                except Exception as e:
                    display('MANAGED-SECRET: could not create new managed secret')
                    raise e
            else:
                raise Exception("Unsupported password generation engine.")

    def get(self):
        return self.current_data.get(self.key)

    def read(self):
        # just alias the method
        return self.get()
