#! /usr/bin/env python

from setuptools import setup

setup(name='run_manager',
      version='1.0.0',
      description='A utility for tracking and reproducing Tensorflow runs.',
      url='https://github.com/lobachevzky/run_manager',
      author='Ethan Brooks',
      author_email='ethanbrooks@gmail.com',
      license='MIT',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Topic :: Scientific/Engineering :: Artificial Intelligence',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
      ],
      keywords='tensorflow utilities development',
      py_modules='runs',
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
