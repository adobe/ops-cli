#Copyright 2019 Adobe. All rights reserved.
#This file is licensed to you under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License. You may obtain a copy
#of the License at http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software distributed under
#the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#OF ANY KIND, either express or implied. See the License for the specific language
#governing permissions and limitations under the License.

from setuptools import setup, find_packages
import os
import sys

_mydir = os.path.abspath(os.path.dirname(sys.argv[0]))
_requires = [ r for r in open(os.path.sep.join((_mydir,'requirements.txt')), "r").read().split('\n') if len(r)>1 ]
setup(
    name='ops',
    version='0.21',
    description='Ops simple wrapper',
    author='Adobe',
    author_email='noreply@adobe.com',
    url='https://github.com/adobe/ops-cli',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    package_data={
        '': ['data/ansible/*','data/ansible/tasks/*', 'data/ssh/*']
    },
    install_requires=_requires,
    entry_points={
        'console_scripts': [
            'ops = ops.main:run'
        ]
    }
)
