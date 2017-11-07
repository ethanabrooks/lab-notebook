#! /usr/bin/env python

from setuptools import setup

with open('README.rst') as f:
    long_description = f.read()

setup(name='run-manager',
      version='1.0.4',
      description='A utility for tracking and reproducing Tensorflow runs.',
      long_description=long_description,
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
      ])
