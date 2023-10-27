#!/usr/bin/python3
#
# Copyright 2023 SUSE LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# -*- coding: utf-8 -*-

"""Setup script."""

# Copyright (c) 2023 SUSE LLC
#
# This file is part of csp-billing-adapter-microsoft.

from setuptools import setup

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('requirements.txt') as req_file:
    requirements = req_file.read().splitlines()

with open('requirements-test.txt') as req_file:
    test_requirements = req_file.read().splitlines()[2:]

with open('requirements-dev.txt') as req_file:
    dev_requirements = test_requirements + req_file.read().splitlines()[2:]


setup(
    name='csp-billing-adapter-microsoft',
    version='0.2.1',
    description='TBD',
    long_description=readme,
    long_description_content_type='text/markdown',
    author='SUSE',
    author_email='public-cloud-dev@susecloud.net',
    url='https://github.com/SUSE-Enceladus/csp-billing-adapter-microsoft',
    entry_points={
        'csp_billing_adapter': [
            'microsoft = csp_billing_adapter_microsoft.plugin'
        ]
    },
    packages=['csp_billing_adapter_microsoft'],
    include_package_data=True,
    python_requires='>=3.6',
    install_requires=requirements,
    extras_require={
        'dev': dev_requirements,
        'test': test_requirements
    },
    license='Apache-2.0',
    zip_safe=False,
    keywords='csp-billing-adapter-microsoft csp_billing_adapter_microsoft',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: Apache License 2.0',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ]
)
