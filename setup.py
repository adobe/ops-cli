# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

import os
import sys

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

with open('README.md') as f:
    _readme = f.read()

_mydir = os.path.abspath(os.path.dirname(sys.argv[0]))
_requires = [r for r in open(os.path.sep.join((_mydir, 'requirements.txt')), "r").read().split('\n') if len(r) > 1]
setup(
    name='ops-cli',
    version='2.0.6',
    description='Ops - wrapper for Terraform, Ansible, and SSH for cloud automation',
    long_description=_readme + '\n\n',
    long_description_content_type='text/markdown',
    url='https://github.com/adobe/ops-cli',
    python_requires='>=3.5',
    author='Adobe',
    author_email='noreply@adobe.com',
    license='Apache2',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Markup :: HTML'
    ],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    package_data={
        '': ['data/ansible/*', 'data/ansible/tasks/*', 'data/ssh/*', 'data/terraform/*']
    },
    install_requires=_requires,
    entry_points={
        'console_scripts': [
            'ops = ops.main:run'
        ]
    }
)
