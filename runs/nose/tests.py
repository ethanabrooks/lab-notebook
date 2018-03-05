import os
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

import yaml
from anytree import ChildResolverError
from anytree import Resolver
from git.util import cwd
from nose.tools import assert_in, eq_, ok_
from nose.tools import assert_not_equal
from nose.tools import assert_not_in
from nose.tools import assert_raises

from runs import main
from runs.db import DBPath, read
from runs.util import NAME, cmd

CHILDREN = 'children'


def sessions():
    try:
        output = subprocess.run('tmux list-session -F "#{session_name}"'.split(),
                                universal_newlines=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE).stdout
        assert isinstance(output, str)
        return output.split('\n')
    except subprocess.CalledProcessError:
        return []


def quote(string):
    return '"' + string + '"'


def get_name(nodes, name):
    return next(n for n in nodes if n[NAME] == name)


def param_generator():
    for path in ['test_run', 'subdir/test_run']:
        for dir_names in [[], ['checkpoints', 'tensorboard']]:
            for flags in [[], ['--option=1']]:
                yield path, dir_names, flags


def param_generator2():
    yield 'test_run', [], []


class Tests:
    def __init__(self):
        self.command = """\
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--option', default=0)
print(vars(parser.parse_args()))\
"""
        self.work_dir = '/tmp/test-run-manager'
        self.db_path = Path(self.work_dir, 'runs.yml')
        self.root = '.runs'
        self.description = 'test new command'
        self.name = 'test_run'
        self.sep = DBPath('').sep

    @property
    def db(self):
        with self.db_path.open() as f:
            return yaml.load(f)

    def db_entry(self, path):
        if not path:
            return self.db
        *path, name = path.split(self.sep)
        entry = self.db_entry(self.sep.join(path))
        assert_in(CHILDREN, entry)
        return get_name(entry[CHILDREN], name)

    @contextmanager
    def _setup(self, path, dir_names, flags):
        assert isinstance(path, str)
        assert isinstance(dir_names, list)
        assert isinstance(flags, list)
        Path(self.work_dir).mkdir(exist_ok=True)
        os.chdir(self.work_dir)
        if any([dir_names, flags]):
            with Path(self.work_dir, '.runsrc').open('w') as f:
                f.write(
                    """\
    [filesystem]
    root = {}
    db_path = runs.yml
    dir_names = {}

    [flags]
    {}\
    """.format(self.root, ' '.join(dir_names), '\n'.join(flags)))
        cmd(['git', 'init', '-q'], cwd=self.work_dir)
        with Path(self.work_dir, '.gitignore').open('w') as f:
            f.write('.runsrc\nruns.yml')
        cmd(['git', 'add', '.gitignore'], cwd=self.work_dir)
        cmd(['git', 'commit', '-qam', 'init'], cwd=self.work_dir)
        main.main(['new', path, self.command, "--description=" + self.description, '-q'])
        yield
        cmd('tmux kill-session -t'.split() + [path], fail_ok=True)
        shutil.rmtree(self.work_dir)

    def check_new(self, path, dir_names, flags):
        name = path.split(self.sep)[-1]

        # test tmux
        assert_in(quote(path), sessions())

        entry = self.db_entry(path)

        # check values that should probably be mocks
        for key in ['commit', 'datetime']:
            assert_in(key, entry)

        # check known values
        attrs = dict(description=self.description,
                     input_command=self.command,
                     name=name)
        for key, attr in attrs.items():
            assert_in(key, entry)
            eq_(entry[key], attr)
        for flag in flags:
            assert_in(flag, entry['full_command'])

        # check file structure
        for dir_name in dir_names:
            path = Path(self.work_dir, self.root, dir_name, path)
            ok_(path.exists(), msg="{} does not exist.".format(path))

    def check_rm(self, path):
        # test tmux
        assert_not_in(quote(path), sessions())

        with assert_raises(ChildResolverError):
            Resolver().get(read(self.db_path), path)

        # check file structure
        for root, dirs, files in os.walk(self.work_dir):
            for file in files:
                assert_not_equal(path, file)

    def test_new(self):
        for path, dir_names, flags in param_generator():
            with self._setup(path, dir_names, flags):
                yield self.check_new, path, dir_names, flags

    def test_remove(self):
        for path, dir_names, flags in param_generator():
            with self._setup(path, dir_names, flags):
                main.main(['rm', '-y', path])
                yield self.check_rm, path

                # TODO: patterns
                # TODO: sad path
