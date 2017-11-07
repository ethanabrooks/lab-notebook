#! /usr/bin/env python

from setuptools import setup

setup(name='run-manager',
      version='1.0.0',
      description='A utility for tracking and reproducing Tensorflow runs.',
      long_description='Machine learning engineers often run multiple versions of an algorithm concurrently. However, '
                       'this can make keeping track of and reproducing runs difficult. This simple utility solves '
                       'this problem by maintaining a database in human-readable YAML formal that tracks a unique '
                       'name assigned to each run, a description of each run, the exact command used for the run, '
                       'the date and time of the run, the most recent commit before the run.',
      url='https://github.com/lobachevzky/run_manager',
      author='Ethan Brooks',
      author_email='ethanbrooks@gmail.com',
      license='MIT',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: Scientific/Engineering :: Artificial Intelligence',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
      ],
      keywords='tensorflow utilities development',
      py_modules='run_manager',
      entry_points={
          'console_scripts': [
              'runs = run_manager:main',
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
