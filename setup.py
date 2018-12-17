#! /usr/bin/env python
# stdlib
# stdlib
# stdlib
# stdlib
# stdlib
# stdlib
# stdlib
import codecs

# third party
from setuptools import setup

with codecs.open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='lab-notebook',
    version='3.3.1',
    description='A utility for tracking, documenting, and reproducing software runs.',
    long_description=long_description,
    url='https://github.com/lobachevzky/lab-notebook',
    author='Ethan Brooks',
    author_email='ethanbrooks@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='tensorflow utilities development',
    packages=['runs'],
    entry_points={
        'console_scripts': [
            'runs = runs.main:main',
            'convert-to-db = runs.convert_to_db:main',
        ],
    },
    scripts=['runs-git'],
    install_requires=[
        'tabulate==0.8.1',
        'nose==1.3.7',
    ])
