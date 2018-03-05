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
COMMAND = """\
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--option', default=0)
print(vars(parser.parse_args()))\
"""
WORK_DIR = '/tmp/test-run-manager'
DB_PATH = Path(WORK_DIR, 'runs.yml')
ROOT = '.runs'
DESCRIPTION = 'test new command'
SEP = '/'


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
        with DB_PATH.open() as f:
            return yaml.load(f)
    *path, name = path.split(SEP)
    entry = db_entry(SEP.join(path))
    assert_in(CHILDREN, entry)
    return get_name(entry[CHILDREN], name)


@contextmanager
def _setup(path, dir_names, flags):
    assert isinstance(path, str)
    assert isinstance(dir_names, list)
    assert isinstance(flags, list)
    Path(WORK_DIR).mkdir(exist_ok=True)
    os.chdir(WORK_DIR)
    if any([dir_names, flags]):
        with Path(WORK_DIR, '.runsrc').open('w') as f:
            f.write(
                """\
[filesystem]
root = {}
db_path = runs.yml
dir_names = {}

[flags]
{}\
""".format(ROOT, ' '.join(dir_names), '\n'.join(flags)))
    cmd(['git', 'init', '-q'], cwd=WORK_DIR)
    with Path(WORK_DIR, '.gitignore').open('w') as f:
        f.write('.runsrc\nruns.yml')
    cmd(['git', 'add', '.gitignore'], cwd=WORK_DIR)
    cmd(['git', 'commit', '-qam', 'init'], cwd=WORK_DIR)
    main.main(['new', path, COMMAND, "--description=" + DESCRIPTION, '-q'])
    yield
    cmd('tmux kill-session -t'.split() + [path], fail_ok=True)
    shutil.rmtree(WORK_DIR)


def check_tmux_new(path):
    assert_in(quote(path), sessions())


def check_db_new(path, flags):
    entry = db_entry(path)

    # check values that should probably be mocks
    for key in ['commit', 'datetime']:
        assert_in(key, entry)

    # check known values
    name = path.split(SEP)[-1]
    attrs = dict(description=DESCRIPTION,
                 input_command=COMMAND,
                 name=name)
    for key, attr in attrs.items():
        assert_in(key, entry)
        eq_(entry[key], attr)
    for flag in flags:
        assert_in(flag, entry['full_command'])


def check_files_new(path, dir_names):
    for dir_name in dir_names:
        path = Path(WORK_DIR, ROOT, dir_name, path)
        ok_(path.exists(), msg="{} does not exist.".format(path))


def check_tmux_rm(path):
    assert_not_in(quote(path), sessions())


def check_db_rm(path):
    with assert_raises(ChildResolverError):
        Resolver().get(read(DB_PATH), path)


def check_files_rm(path):
    for root, dirs, files in os.walk(WORK_DIR):
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
