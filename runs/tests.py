import os
import shutil
import subprocess
from contextlib import contextmanager
from fnmatch import fnmatch
from pathlib import Path
from pprint import pprint

import yaml
from anytree import ChildResolverError
from anytree import PreOrderIter
from anytree import Resolver
from nose.tools import assert_false
from nose.tools import assert_in, eq_, ok_
from nose.tools import assert_is_instance
from nose.tools import assert_not_in
from nose.tools import assert_raises
import nose.tools

from runs import db
from runs import main
from runs.cfg import Cfg
from runs.db import read
from runs.pattern import Pattern
from runs.run import Run
from runs.util import NAME, cmd

# TODO: sad path

CHILDREN = 'children'
SCRIPT = """\
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--option', default=0)
print(vars(parser.parse_args()))\
"""
COMMAND = 'python test.py'
WORK_DIR = '/tmp/test-run-manager'
DB_PATH = Path(WORK_DIR, 'runs.yml')
ROOT = WORK_DIR + '/.runs'
DESCRIPTION = 'test new command'
SEP = '/'
SUBDIR = 'subdir'
TEST_RUN = 'test_run'
DEFAULT_CFG = Cfg(root=ROOT, db_path=DB_PATH, quiet=True)


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


class ParamGenerator:
    def __init__(self, paths=None, dir_names=None, flags=None):
        if paths is None:
            paths = [TEST_RUN]
        if dir_names is None:
            dir_names = [[], ['checkpoints', 'tensorboard']]
        if flags is None:
            flags = [[], ['--option=1']]
        self.paths = paths
        self.dir_names = dir_names
        self.flags = flags

    def __iter__(self):
        for path in self.paths:
            for dir_names in self.dir_names:
                for flags in self.flags:
                    yield path, dir_names, flags

    def __next__(self):
        return next(iter(self))

    def __add__(self, other):
        assert isinstance(other, ParamGenerator)
        return ParamGenerator(self.paths + other.paths,
                              self.dir_names + other.dir_names,
                              self.flags + other.flags)


class SimpleParamGenerator(ParamGenerator):
    def __init__(self):
        super().__init__([TEST_RUN], [['checkpoints', 'tensorboard']], [[]])


class ParamGeneratorWithSubdir(ParamGenerator):
    def __init__(self):
        super().__init__(paths=[SUBDIR + SEP + TEST_RUN, SUBDIR + SEP + SUBDIR + SEP + TEST_RUN])


class ParamGeneratorWithPatterns(ParamGenerator):
    def __init__(self):
        super().__init__(paths=['*', 'subdir/*', 'test*'])


def db_entry(path):
    if not path:
        with DB_PATH.open() as f:
            return yaml.load(f)

    # recursively get entry from one level up
    *path, name = path.split(SEP)
    entry = db_entry(SEP.join(path))

    # find name in current level
    assert_in(CHILDREN, entry)
    return get_name(entry[CHILDREN], name)


# TODO what if config doesn't have required fields?

@contextmanager
def _setup(path, dir_names=None, flags=None):
    if dir_names is None:
        dir_names = []
    if flags is None:
        flags = []
    assert isinstance(path, str)
    assert isinstance(dir_names, list)
    assert isinstance(flags, list)
    Path(WORK_DIR).mkdir(exist_ok=True)
    os.chdir(WORK_DIR)
    if any([dir_names, flags]):
        with Path(WORK_DIR, '.runsrc').open('w') as f:
            f.write(
                """\
[multi]
root = {}
db_path = {}
dir_names = {}

[flags]
{}\
""".format(ROOT, DB_PATH, ' '.join(dir_names), '\n'.join(flags)))
    cmd(['git', 'init', '-q'], cwd=WORK_DIR)
    with Path(WORK_DIR, '.gitignore').open('w') as f:
        f.write('.runsrc')
    with Path(WORK_DIR, 'test.py').open('w') as f:
        f.write(SCRIPT)
    cmd(['git', 'add', '--all'], cwd=WORK_DIR)
    cmd(['git', 'commit', '-am', 'init'], cwd=WORK_DIR)
    main.main(['-q', 'new', path, COMMAND, "--description=" + DESCRIPTION])
    yield
    cmd('tmux kill-session -t'.split() + [path], fail_ok=True)
    shutil.rmtree(WORK_DIR, ignore_errors=True)


def check_tmux(path):
    assert_in(quote(path), sessions())


def check_db(path, flags):
    entry = db_entry(path)

    # check values that should probably be mocks
    for key in ['commit', 'datetime']:
        assert_in(key, entry)

    # check known values
    name = path.split(SEP)[-1]
    attrs = dict(description=DESCRIPTION,
                 _input_command=COMMAND,
                 name=name)
    for key, attr in attrs.items():
        assert_in(key, entry)
        eq_(entry[key], attr)
    for flag in flags:
        assert_in(flag, entry['full_command'])


def check_files(path, dir_names):
    for dir_name in dir_names:
        path = Path(ROOT, dir_name, path)
        ok_(path.exists(), msg="{} does not exist.".format(path))


def check_tmux_killed(path):
    assert_not_in(quote(path), sessions())


def check_del_entry(path):
    with assert_raises(ChildResolverError):
        Resolver().glob(read(DB_PATH), path)


def check_rm_files(path):
    for root, dirs, files in os.walk(ROOT):
        for filename in files:
            assert_false(fnmatch(filename, path))


def test_new():
    for path, dir_names, flags in ParamGenerator():
        with _setup(path, dir_names, flags):
            yield check_tmux, path
            yield check_db, path, flags
            yield check_files, path, dir_names


def test_rm():
    for path, dir_names, flags in ParamGenerator() + ParamGeneratorWithSubdir():
        with _setup(path, dir_names, flags):
            main.main(['-q', 'rm', '-y', path])
            yield check_tmux_killed, path
            yield check_del_entry, path
            yield check_rm_files, path

            # TODO: patterns


def check_list_happy(pattern, print_attrs):
    string = Pattern(pattern).tree_string(print_attrs)
    if print_attrs:
        assert_in('test_run', string)
        assert_in('commit', string)
    else:
        eq_(string, """\
.
└── test_run
""")


def check_list_sad(pattern):
    string = Pattern(pattern, cfg=DEFAULT_CFG).tree_string()
    eq_(string, '.\n')


def test_list():
    path = TEST_RUN
    for _, dir_names, flags in ParamGenerator():
        with _setup(path, dir_names, flags):
            for pattern in ['*', 'test*']:
                for print_attrs in range(2):
                    yield check_list_happy, pattern, print_attrs
            for pattern in ['x*', 'test']:
                yield check_list_sad, pattern


def check_table(table):
    assert_is_instance(table, str)
    for member in [COMMAND, DESCRIPTION, TEST_RUN]:
        assert_in(member, table)


def test_table():
    with _setup(TEST_RUN):
        yield check_table, Pattern('*').table(100)
        yield check_table, db.table(PreOrderIter(db.read(DB_PATH)), [], 100)


def test_lookup():
    with _setup(TEST_RUN):
        pattern = Pattern('*', cfg=DEFAULT_CFG)
        for key, value in dict(name=TEST_RUN,
                               description=DESCRIPTION,
                               _input_command=COMMAND).items():
            eq_(pattern.lookup(key), [value])
        with assert_raises(SystemExit):
            pattern.lookup('x')


def test_chdesc():
    with _setup(TEST_RUN):
        description = 'new description'
        main.main(['chdesc', TEST_RUN, '--description=' + description])
        eq_(Run(TEST_RUN).lookup('description'), description)


def check_move(path, new_path, dir_names=None, flags=None):
    if dir_names is None:
        dir_names = []
    if flags is None:
        flags = []
    check_del_entry(path)
    check_rm_files(path)
    check_db(new_path, flags)
    check_files(new_path, dir_names)


def test_move():
    generator = ParamGenerator() + ParamGeneratorWithSubdir()
    for path, dir_names, flags in generator:
        for new_path in generator.paths:
            with _setup(path, dir_names, flags):
                args = ['mv', '-y', '--keep-tmux', path, new_path]
                if path != new_path:
                    main.main(args)
                    yield check_move, path, new_path, dir_names, flags
                    yield check_tmux, new_path.split('/')[-1]


def test_move_dirs():
    with _setup('sub/sub/test_run'):
        main.main(['mv', '-y', 'sub/sub/test_run', 'new_dir/'])
        # dest is dir -> move src into dest
        yield check_move, 'sub/sub/test_run', 'new_dir/test_run'
        yield check_del_entry, 'sub'
        yield check_rm_files, 'sub'

    with _setup('sub/test_run'):
        main.main(['mv', '-y', 'sub', 'new_dir'])
        # src is dir -> change src to dest and bring children
        yield check_move, 'sub/test_run', 'new_dir/test_run'

    with _setup('sub/sub/test_run'):
        main.main(['mv', '-y', 'sub/sub', 'sub/new_dir'])
        # src is dir -> change src to dest and bring children
        yield check_move, 'sub/sub/test_run', 'sub/new_dir/test_run'

    with _setup('sub/test_run'):
        main.main(['mv', '-y', 'sub', 'new_dir/'])
        # src is dir and dest is dir -> move src into dest and bring children
        yield check_move, 'sub/test_run', 'new_dir/sub/test_run'

    with _setup('sub/sub1/test_run'):
        main.main(['mv', '-y', 'sub/sub1/', '.'])
        # src is dir and dest is dir -> move src into dest and bring children
        yield check_move, 'sub/sub1/test_run', 'sub1/test_run'

    with _setup('sub/test_run1'), _setup('sub/test_run2'):
        main.main(['mv', '-y', 'sub/*', 'new'])
        # src is multi -> for each node match, move head into dest
        yield check_move, 'sub/test_run1', 'new/test_run1'
        yield check_move, 'sub/test_run2', 'new/test_run2'

    with _setup('sub/sub1/test_run1'), _setup('sub/sub2/test_run2'):
        main.main(['mv', '-y', 'sub/*', 'new'])
        # src is multi -> for each node match, move head into dest
        yield check_move, 'sub/sub1/test_run1', 'new/sub1/test_run1'
        yield check_move, 'sub/sub2/test_run2', 'new/sub2/test_run2'

    with _setup('sub1/test_run1'), _setup('sub2/test_run2'):
        main.main(['mv', '-y', 'sub1/test_run1', 'sub2'])
        # dest is dir -> move node into dest
        yield check_move, 'sub1/test_run1', 'sub2/test_run1'

    with _setup('sub1/sub1/test_run1'), _setup('sub2/test_run2'):
        main.main(['mv', '-y', 'sub1/sub1', 'sub2'])
        # dest is dir and src is dir -> move node into dest
        yield check_move, 'sub1/sub1/test_run1', 'sub2/sub1/test_run1'
