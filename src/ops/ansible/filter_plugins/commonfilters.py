#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

from __future__ import absolute_import
import os
from ops.cli import display
from six import iteritems


def read_file(fname):
    if os.path.exists(fname):
        with open(fname) as f:
            return f.read()
    else:
        display("read_file: File %s does not exist" % fname, stderr=True, color='red')
        return None

def write_file(fname, contents):
    handler = open(fname,'w')
    handler.write(contents)
    handler.close()

def escape_new_lines(string):
    return string.replace("\n", "\\n")

def read_consul(key_path, consul_url="http://localhost:8500", recurse=True, show_error=False):
    ret = {}
    try:
        from ops.simpleconsul import SimpleConsul
        sc = SimpleConsul(consul_url)
        ret = sc.get(key_path,recurse)
    except Exception as e:
        if show_error:
            ret['error'] = e.message
    return ret

def read_envvar(varname, default=None):
    import os
    return os.getenv(varname,default)

def read_yaml(fname, show_error=False):
    ret = {}
    try:
        import yaml as y
        f = open(fname,"r")
        ret = y.safe_load(f.read())
    except Exception as e:
        if show_error:
            ret['error'] = e.message
    return ret

def flatten_tree(d, parent_key='', sep='/'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + str(k) if parent_key else str(k)
        if isinstance(v, dict):
            items.extend(flatten_tree(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def check_vault(
        secret_path, key='value', vault_user=None, vault_url=None,
        token=None, namespace=None, mount_point=None, auto_prompt=True):

    from ops.simplevault import SimpleVault
    sv = SimpleVault(
        vault_user=vault_user, vault_addr=vault_url, vault_token=token, 
        namespace=namespace, mount_point=mount_point, auto_prompt=auto_prompt)
    check_status = sv.check(secret_path, key)
    # we want to return these string values because this is what Jinja2 understands
    if check_status:
        return "true"
    return "false"

def read_vault(
        secret_path, key='value', fetch_all=False, vault_user=None, vault_url=None,
        token=None, namespace=None, mount_point=None, auto_prompt=True):

    from ops.simplevault import SimpleVault
    sv = SimpleVault(
        vault_user=vault_user, vault_addr=vault_url, vault_token=token, 
        namespace=namespace, mount_point=mount_point, auto_prompt=auto_prompt)
    return sv.get(path=secret_path, key=key, fetch_all=fetch_all)

def write_vault(
        secret_path, key='value', data="", vault_user=None, vault_url=None, 
        namespace=None, mount_point=None, token=None, auto_prompt=True):

    from ops.simplevault import  SimpleVault
    sv = SimpleVault(
        vault_user=vault_user, vault_addr=vault_url, vault_token=token, 
        namespace=None, mount_point=None, auto_prompt=auto_prompt)
    new_data = {}
    if isinstance(data, dict):
        for k,v in iteritems(data):
            new_data[k] = str(v)
    elif key:
        new_data[key] = str(data)
    else:
        return False
    return sv.put(path=secret_path, value=new_data )

def read_ssm(key, aws_profile, region_name='us-east-1'):
    from ops.simplessm import SimpleSSM
    ssm = SimpleSSM(aws_profile, region_name)
    return ssm.get(key)

def managed_vault_secret(secret_path,key='value',
                         policy={},
                         vault_user=None,
                         vault_addr=None,
                         vault_token=None,
                         namespace=None,
                         mount_point=None,
                         auto_prompt=True):
    from ops.simplevault import ManagedVaultSecret
    ms = ManagedVaultSecret(path=secret_path,
                            key=key,
                            policy=policy,
                            vault_user=vault_user,
                            vault_addr=vault_addr,
                            vault_token=vault_token,
                            namespace=namespace,
                            mount_point=mount_point,
                            auto_prompt=auto_prompt)
    return ms.get()

def escape_json(input):
    import json
    escaped = json.dumps(input)
    if escaped.startswith('"') and escaped.endswith('"'):
        # trim double quotes
        return escaped[1:-1]
    return escaped

class FilterModule(object):
    
    def filters(self):
        return {
            'escape_new_lines': escape_new_lines,
            'flatten_tree': flatten_tree,
            'read_consul': read_consul,
            'read_envvar': read_envvar,
            'read_file': read_file,
            'read_vault': read_vault,
            'read_yaml': read_yaml,
            'write_vault': write_vault,
            'managed_vault_secret': managed_vault_secret,
            'read_ssm': read_ssm,
            'escape_json': escape_json,
            'check_vault': check_vault
        }
