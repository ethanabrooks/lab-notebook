#! /usr/bin/env python

from setuptools import setup
setup(name='run_manager',
      entry_points={
          'console_scripts': [
              'runs = runs:main',
          ],
      },
      install_requires=[
          'paramiko==2.3.1',
          'GitPython==2.1.7',
          'libtmux==0.7.5',
          'termcolor==1.1.0',
          'PyYAML==3.12',
          'tabulate==0.8.1',
          'pygame==1.9.3',
      ])
