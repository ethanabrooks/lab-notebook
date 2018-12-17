# stdlib
from contextlib import contextmanager
from fnmatch import fnmatch
import os
from pathlib import Path
import shutil
import subprocess

# third party
from nose.tools import assert_false, assert_in, assert_is_instance, assert_not_in, assert_raises, eq_, ok_

# first party
from runs import main
from runs.commands import lookup, ls
from runs.database import DataBase
from runs.logger import UI
from runs.shell import Bash

# TODO: sad path

SCRIPT = """\
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--option', default=0)
print(vars(parser.parse_args()))\
"""
COMMAND = 'python3 test.py'
WORK_DIR = '/tmp/test-run-manager'
DB_PATH = Path(WORK_DIR, 'runs.db')
ROOT = WORK_DIR + '/.runs'
DESCRIPTION = "test 'new' command"
SEP = '/'
SUBDIR = 'subdir'
TEST_RUN = 'test_run'

LOGGER = UI(quiet=True, assume_yes=True)
BASH = Bash(logger=LOGGER)
DB = DataBase(DB_PATH, LOGGER)


def sessions():
    try:
        output = BASH.cmd('tmux list-session -F "#{session_name}"'.split(), fail_ok=True)
        assert isinstance(output, str)
        return output.split('\n')
    except subprocess.CalledProcessError:
        return []


def quote(string):
    return '"' + string + '"'


class ParamGenerator:
    def __init__(self, paths=None, dir_names=None, flags=None):
        if paths is None:
            paths = [TEST_RUN]
        if dir_names is None:
            dir_names = [[], ['checkpoints', 'tensorboard']]
        if flags is None:
            flags = [[], ['--option=1'], ['--option=1', '--option=2']]
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
        return ParamGenerator(self.paths + other.paths, self.dir_names + other.dir_names,
                              self.flags + other.flags)


class SimpleParamGenerator(ParamGenerator):
    def __init__(self):
        super().__init__([TEST_RUN], [['checkpoints', 'tensorboard']], [[]])


class ParamGeneratorWithSubdir(ParamGenerator):
    def __init__(self):
        super().__init__(
            paths=[SUBDIR + SEP + TEST_RUN, SUBDIR + SEP + SUBDIR + SEP + TEST_RUN])


class ParamGeneratorWithPatterns(ParamGenerator):
    def __init__(self):
        super().__init__(paths=['%', 'subdir/%', 'test%'])


# TODO what if config doesn't have required fields?


def run_main(*args):
    main.main(['-q', '-y'] + list(args))


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
        flag_string = '\n\t'.join(flags)
        with Path(WORK_DIR, '.runsrc').open('w') as f:
            f.write(f"""\
[main]
root : {ROOT}
db_path : {DB_PATH}
dir_names : {' '.join(dir_names)}
flags : {flag_string}
""")
    BASH.cmd(['git', 'init', '-q'], cwd=WORK_DIR)
    with Path(WORK_DIR, '.gitignore').open('w') as f:
        f.write('.runsrc')
    with Path(WORK_DIR, 'test.py').open('w') as f:
        f.write(SCRIPT)
    BASH.cmd(['git', 'add', '--all'], cwd=WORK_DIR)
    BASH.cmd(['git', 'commit', '-am', 'init'], cwd=WORK_DIR)
    run_main('new', f'--path={path}', f'--command={COMMAND}',
             f'--description="{DESCRIPTION}"')
    yield
    BASH.cmd('tmux kill-session -t'.split() + [path], fail_ok=True)
    shutil.rmtree(WORK_DIR, ignore_errors=True)


def check_tmux(path):
    assert_in(quote(path), sessions())


def check_db(path, flags):
    with DB as db:
        # check known values
        runs = db.get(path + '%')
        assert_in(DESCRIPTION, lookup.string(
            runs=runs,
            key='description',
        ))
        assert_in(COMMAND, lookup.string(
            runs=runs,
            key='command',
        ))
        assert_in(path, lookup.string(
            runs=runs,
            key='path',
        ))
        for flag in flags:
            assert_in(flag, lookup.string(
                runs=runs,
                key='command',
            ))


def check_files(path, dir_names):
    for dir_name in dir_names:
        path = Path(ROOT, dir_name, path)
        ok_(path.exists(), msg="{} does not exist.".format(path))


def check_tmux_killed(path):
    assert_not_in(quote(path), sessions())


def check_del_entry(path):
    with DB as db:
        assert_not_in(path, db.get(path))


def check_rm_files(path):
    for root, dirs, files in os.walk(ROOT):
        for filename in files:
            assert_false(fnmatch(filename, path))


def check_list_happy(pattern):
    with DB as db:
        runs = db.get(pattern)
        string = ls.string(runs=runs)
        assert_in('test_run', string)


def check_list_sad(pattern):
    with DB as db:
        string = ls.string(runs=db.get([pattern]))
        eq_(string, '')


def check_move(path, new_path, dir_names=None, flags=None):
    if dir_names is None:
        dir_names = []
    if flags is None:
        flags = []
    check_del_entry(path)
    check_rm_files(path)
    check_db(new_path, flags)
    check_files(new_path, dir_names)


def test_new():
    for path, dir_names, flags in ParamGenerator():
        with _setup(path, dir_names, flags):
            yield check_tmux, path
            yield check_db, path, flags
            yield check_files, path, dir_names


def test_rm():
    for path, dir_names, flags in ParamGenerator() + ParamGeneratorWithSubdir():
        with _setup(path, dir_names, flags):
            run_main('rm', path)
            yield check_tmux_killed, path
            yield check_del_entry, path
            yield check_rm_files, path


def test_list():
    path = TEST_RUN
    for _, dir_names, flags in ParamGenerator():
        with _setup(path, dir_names, flags):
            for pattern in ['%', 'test%']:
                yield check_list_happy, pattern
            for pattern in ['x%', 'x']:
                yield check_list_sad, pattern


def test_lookup():
    with _setup(TEST_RUN), DB as db:
        for key, value in dict(
                path=TEST_RUN, description=DESCRIPTION, command=COMMAND).items():
            assert_in(value, lookup.string(runs=db.get([TEST_RUN]), key=key))
        with assert_raises(SystemExit):
            run_main('lookup', 'x', TEST_RUN)


def test_chdesc():
    with _setup(TEST_RUN), DB as db:
        description = 'new description'
        run_main('change-description', TEST_RUN, description)
        assert_in(description, lookup.string(runs=db.get([TEST_RUN]), key='description'))


def test_move():
    generator = ParamGenerator() + ParamGeneratorWithSubdir()
    for path, dir_names, flags in generator:
        for new_path in generator.paths:
            with _setup(path, dir_names, flags):
                if path != new_path:
                    run_main('mv', path, new_path)
                    yield check_move, path, new_path, dir_names, flags
                    yield check_tmux, new_path


def move(src, dest):
    run_main('mv', src, dest)


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

    with _setup('sub/test_run'), _setup('sub2/test_run2'):
        move('sub', 'sub2')
        # src is dir and dest is dir -> move src into dest and bring children
        yield check_move, 'sub/test_run', 'sub2/sub/test_run'

    with _setup('sub/sub1/test_run'):
        move('sub/sub1/', '.')
        # src is dir and dest is dir -> move src into dest and bring children
        yield check_move, 'sub/sub1/test_run', 'sub1/test_run'

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
        with DB as db:
            assert_in('--run1', lookup.string(runs=db.get(['test_run2']), key='command'))

    with _setup('test'):
        move('test', 'test/test2')
        # move into self; this is a problem for movedir
        yield check_move, 'test', 'test/test2'

    # with _setup('test_run1'), _setup('test_run2'):
    #     # src is multi, dest is run -> create dir with same name as dest
    #     #                              and move into dir
    #     move('test_run%', 'test_run2')
    #     yield check_move, 'test_run1', 'test_run2/test_run1'
    #     yield check_move, 'test_run2', 'test_run2/test_run2'
