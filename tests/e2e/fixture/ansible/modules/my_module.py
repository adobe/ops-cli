#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

#!/usr/bin/env python
def main():
    module = AnsibleModule(
        argument_spec=dict(
            set_facts=dict(required=True, type='dict')
        )
    )

    result = dict(
        changed=True,
        ansible_facts=module.params['set_facts']
    )

    module.exit_json(**result)


from ansible.module_utils.basic import *

main()
