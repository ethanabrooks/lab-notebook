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
command = """\
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--option', default=0)
print(vars(parser.parse_args()))\
"""
work_dir = '/tmp/test-run-manager'
db_path = Path(work_dir, 'runs.yml')
root = '.runs'
description = 'test new command'
name = 'test_run'
sep = DBPath('').sep


def sessions():
    try:
        output = cmd('tmux list-session -F "#{session_name}"'.split(), fail_ok=True)
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


def db_entry(path):
    if not path:
        with db_path.open() as f:
            return yaml.load(f)
    *path, name = path.split(sep)
    entry = db_entry(sep.join(path))
    assert_in(CHILDREN, entry)
    return get_name(entry[CHILDREN], name)


@contextmanager
def _setup(path, dir_names, flags):
    assert isinstance(path, str)
    assert isinstance(dir_names, list)
    assert isinstance(flags, list)
    Path(work_dir).mkdir(exist_ok=True)
    os.chdir(work_dir)
    if any([dir_names, flags]):
        with Path(work_dir, '.runsrc').open('w') as f:
            f.write(
                """\
[filesystem]
root = {}
db_path = runs.yml
dir_names = {}

[flags]
{}\
""".format(root, ' '.join(dir_names), '\n'.join(flags)))
    cmd(['git', 'init', '-q'], cwd=work_dir)
    with Path(work_dir, '.gitignore').open('w') as f:
        f.write('.runsrc\nruns.yml')
    cmd(['git', 'add', '.gitignore'], cwd=work_dir)
    cmd(['git', 'commit', '-qam', 'init'], cwd=work_dir)
    main.main(['new', path, command, "--description=" + description, '-q'])
    yield
    cmd('tmux kill-session -t'.split() + [path], fail_ok=True)
    shutil.rmtree(work_dir)


def check_tmux_new(path):
    assert_in(quote(path), sessions())


def check_db_new(path, flags):
    entry = db_entry(path)

    # check values that should probably be mocks
    for key in ['commit', 'datetime']:
        assert_in(key, entry)

    # check known values
    name = path.split(sep)[-1]
    attrs = dict(description=description,
                 input_command=command,
                 name=name)
    for key, attr in attrs.items():
        assert_in(key, entry)
        eq_(entry[key], attr)
    for flag in flags:
        assert_in(flag, entry['full_command'])


def check_files_new(path, dir_names):
    for dir_name in dir_names:
        path = Path(work_dir, root, dir_name, path)
        ok_(path.exists(), msg="{} does not exist.".format(path))


def check_tmux_rm(path):
    assert_not_in(quote(path), sessions())


def check_db_rm(path):
    with assert_raises(ChildResolverError):
        Resolver().get(read(db_path), path)


def check_files_rm(path):
    for root, dirs, files in os.walk(work_dir):
        for file in files:
            assert_not_equal(path, file)


def test_new():
    for path, dir_names, flags in param_generator():
        with _setup(path, dir_names, flags):
            yield check_tmux_new, path
            yield check_db_new, path, flags
            yield check_files_new, path, dir_names


def test_remove():
    for path, dir_names, flags in param_generator():
        with _setup(path, dir_names, flags):
            main.main(['rm', '-y', path])
            yield check_tmux_rm, path
            yield check_db_rm, path
            yield check_files_rm, path

            # TODO: patterns
            # TODO: sad path
