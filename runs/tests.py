import os
import shutil
import subprocess
from contextlib import contextmanager
from fnmatch import fnmatch
from pathlib import Path

from nose.tools import (assert_false, assert_in, assert_is_instance,
                        assert_not_in, assert_raises, assert_true, eq_, ok_)

from runs import main
from runs.db import Table
from runs.util import CHDESCRIPTION, cmd

# TODO: sad path

SCRIPT = """\
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--option', default=0)
print(vars(parser.parse_args()))\
"""
COMMAND = 'python test.py'
WORK_DIR = '/tmp/test-run-manager'
DB_PATH = Path(WORK_DIR, 'runs.db')
ROOT = WORK_DIR + '/.runs'
DESCRIPTION = 'test new command'
SEP = '/'
SUBDIR = 'subdir'
TEST_RUN = 'test_run'


def sessions():
    try:
        output = cmd(
            'tmux list-session -F "#{session_name}"'.split(), fail_ok=True)
        assert isinstance(output, str)
        return output.split('\n')
    except subprocess.CalledProcessError:
        return []


def quote(string):
    return '"' + string + '"'


def ls(pattern=None, show_attrs=False):
    command = ['runs', 'ls']
    if show_attrs:
        command += ['--show-attrs']
    if pattern:
        command += [pattern]
    return cmd(command).split('\n')


def lookup(path, key):
    return cmd(f'runs lookup {key} {path}'.split())


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
        super().__init__(paths=[
            SUBDIR + SEP + TEST_RUN, SUBDIR + SEP + SUBDIR + SEP + TEST_RUN
        ])


class ParamGeneratorWithPatterns(ParamGenerator):
    def __init__(self):
        super().__init__(paths=['%', 'subdir/%', 'test%'])


# TODO I don't like this.
def db_entry(path):
    with Table(DB_PATH) as table:
        return table[path][0]


# TODO what if config doesn't have required fields?


@contextmanager
def _setup(path, dir_names=None, flags=None):
    if dir_names is None:
        dir_names = []
    if flags is None:
        flags = []
    assert_is_instance(path, str)
    assert_is_instance(dir_names, list)
    assert_is_instance(flags, list)
    Path(WORK_DIR).mkdir(exist_ok=True)
    os.chdir(WORK_DIR)
    if any([dir_names, flags]):
        flag_string = '\n'.join(flags)
        with Path(WORK_DIR, '.runsrc').open('w') as f:
            f.write(f"""\
[main]
root : {ROOT}
db_path : {DB_PATH}
dir_names : {' '.join(dir_names)}

[flags]
{flag_string}
""")
    cmd(['git', 'init', '-q'], cwd=WORK_DIR)
    with Path(WORK_DIR, '.gitignore').open('w') as f:
        f.write('.runsrc')
    with Path(WORK_DIR, 'test.py').open('w') as f:
        f.write(SCRIPT)
    cmd(['git', 'add', '--all'], cwd=WORK_DIR)
    cmd(['git', 'commit', '-am', 'init'], cwd=WORK_DIR)
    main.main(
        ['-q', '-y', 'new', path, COMMAND, "--description=" + DESCRIPTION])
    yield
    cmd('tmux kill-session -t'.split() + [path], fail_ok=True)
    shutil.rmtree(WORK_DIR, ignore_errors=True)


def check_tmux(path):
    assert_in(quote(path), sessions())


def check_db(path, flags):
    entry = db_entry(path)

    # check values that should probably be mocks
    assert_true(entry.commit)
    assert_true(entry.datetime)

    # check known values
    eq_(entry.description, DESCRIPTION)
    eq_(entry.input_command, COMMAND)
    eq_(entry.path, path)
    for flag in flags:
        assert_in(flag, entry.full_command)


def check_files(path, dir_names):
    for dir_name in dir_names:
        path = Path(ROOT, dir_name, path)
        ok_(path.exists(), msg="{} does not exist.".format(path))


def check_tmux_killed(path):
    assert_not_in(quote(path), sessions())


def check_del_entry(path):
    assert_not_in(path, ls())


def check_rm_files(path):
    for root, dirs, files in os.walk(ROOT):
        for filename in files:
            assert_false(fnmatch(filename, path))


#
def test_new():
    for path, dir_names, flags in ParamGenerator():
        with _setup(path, dir_names, flags):
            yield check_tmux, path
            yield check_db, path, flags
            yield check_files, path, dir_names


def test_rm():
    for path, dir_names, flags in ParamGenerator() + ParamGeneratorWithSubdir(
    ):
        with _setup(path, dir_names, flags):
            main.main(['-q', '-y', 'rm', path])
            yield check_tmux_killed, path
            yield check_del_entry, path
            yield check_rm_files, path

            # TODO: patterns


def check_list_happy(pattern, show_attrs):
    # TODO
    string = ls(pattern, show_attrs)
    # if print_attrs:
    #     assert_in('test_run', string)
    #     assert_in('commit', string)
    # else:
    #     pass


#         eq_(string, """\
# .
# └── test_run
# """)


def check_list_sad(pattern):
    # TODO
    string = ls(pattern, show_attrs=True)
    # eq_(string, '.\n')


#
#
def test_list():
    path = TEST_RUN
    for _, dir_names, flags in ParamGenerator():
        with _setup(path, dir_names, flags):
            for pattern in ['%', 'test%']:
                for print_attrs in range(2):
                    yield check_list_happy, pattern, print_attrs
            for pattern in ['x%', 'test']:
                yield check_list_sad, pattern


def check_table(table):
    assert_is_instance(table, str)
    for member in [COMMAND, DESCRIPTION, TEST_RUN]:
        assert_in(member, table)


def test_table():
    pass
    # TODO
    # with _setup(TEST_RUN):
    #     yield check_table, cmd(['runs', 'table'])


def test_lookup():
    with _setup(TEST_RUN):
        for key, value in dict(
                path=TEST_RUN, description=DESCRIPTION,
                input_command=COMMAND).items():
            eq_(lookup(TEST_RUN, key), value)
        with assert_raises(SystemExit):
            main.main(['lookup', 'x', TEST_RUN])


def test_chdesc():
    with _setup(TEST_RUN):
        description = 'new description'
        main.main([CHDESCRIPTION, TEST_RUN, '--description=' + description])
        eq_(lookup(TEST_RUN, 'description'), description)


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
                args = ['-y', 'mv', path, new_path]
                if path != new_path:
                    main.main(args)
                    yield check_move, path, new_path, dir_names, flags
                    yield check_tmux, new_path.split('/')[-1]


def move(src, dest):
    main.main(['-y', 'mv', src, dest])


def test_move_dirs():
    with _setup('sub/test_run'):
        move('sub', 'new_dir')
        # src is dir -> change src to dest and bring children
        yield check_move, 'sub/test_run', 'new_dir/test_run'

    with _setup('sub/sub/test_run'):
        move('sub/sub', 'sub/new_dir')
        # src is dir -> change src to dest and bring children
        yield check_move, 'sub/sub/test_run', 'sub/new_dir/test_run'

    with _setup('sub/test_run'):
        move('sub', 'new_dir')
        # src is dir and dest is dir -> move src into dest and bring children
        yield check_move, 'sub/test_run', 'new_dir/test_run'

    with _setup('sub/test_run'), _setup('new_dir/test_run2'):
        move('sub', 'new_dir')
        # src is dir and dest is dir -> move src into dest and bring children
        yield check_move, 'sub/test_run', 'new_dir/sub/test_run'

    with _setup('sub/sub1/test_run'):
        move('sub/sub1/', '.')
        # src is dir and dest is dir -> move src into dest and bring children
        yield check_move, 'sub/sub1/test_run', 'sub1/test_run'

    # here
    with _setup('sub/test_run1'), _setup('sub/test_run2'):
        move('sub/%', 'new')
        # src is multi -> for each node match, move head into dest
        yield check_move, 'sub/test_run1', 'new/test_run1'
        yield check_move, 'sub/test_run2', 'new/test_run2'

    with _setup('sub/sub1/test_run1'), _setup('sub/sub2/test_run2'):
        move('sub/%', 'new')
        # src is multi -> for each node match, move head into dest
        yield check_move, 'sub/sub1/test_run1', 'new/sub1/test_run1'
        yield check_move, 'sub/sub2/test_run2', 'new/sub2/test_run2'

    with _setup('sub1/test_run1'), _setup('sub2/test_run2'):
        move('sub1/test_run1', 'sub2')
        # dest is dir -> move node into dest
        yield check_move, 'sub1/test_run1', 'sub2/test_run1'

    with _setup('sub1/sub1/test_run1'), _setup('sub2/test_run2'):
        move('sub1/sub1', 'sub2')
        # dest is dir and src is dir -> move node into dest
        yield check_move, 'sub1/sub1/test_run1', 'sub2/sub1/test_run1'

    with _setup('test_run1', flags=['--run1']), _setup('test_run2', flags=['run2']):
        move('test_run1', 'test_run2')
        # dest is run -> overwrite dest
        yield check_move, 'test_run1', 'test_run2'
        assert_in('--run1', db_entry('test_run2').full_command)

    with _setup('test_run1'), _setup('test_run2'), _setup('not_a_dir'):
        # src is multi, dest is run -> exits with no change
        with assert_raises(SystemExit):
            move('test_run%', 'not_a_dir')
        for path in ['test_run1', 'test_run2', 'not_a_dir']:
            yield check_tmux, path
            yield check_db, path, []
            yield check_files, path, []
