#!/usr/bin/env python

#  Copyright (c) 2010 Franz Allan Valencia See
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


"""Setup script for Robot's YamlLibrary distributions"""

import sys
import os
from os.path import join, dirname
from ez_setup import use_setuptools
from setuptools import setup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
use_setuptools()
execfile(join(dirname(__file__), 'src', 'YamlLibrary', 'version.py'))


def main():
    setup(name='robotframework-yamllibrary',
          version=VERSION,
          description='Yaml utility library for Robot Framework',
          author='Fred Huang',
          author_email='divfor@gmail.com',
          url='https://github.com/divfor/robotframework-yamllibrary',
          package_dir={'': 'src'},
          packages=['YamlLibrary'],
          install_requires=['pyyaml >= 3.0'],
          include_package_data=True,
          )

if __name__ == "__main__":
    main()
