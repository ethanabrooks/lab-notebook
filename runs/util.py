import itertools
import shutil
import subprocess
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import List

from termcolor import colored


def highlight(*args):
    string = ' '.join(map(str, args))
    return colored(string, color='blue', attrs=['bold'])


def search_ancestors(filename):
    dirpath = Path('.').resolve()
    while not dirpath.match(dirpath.root):
        filepath = Path(dirpath, filename)
        if filepath.exists():
            return filepath
        dirpath = dirpath.parent


def prune_empty(path):
    assert isinstance(path, Path)

    if path.exists():
        # directory is not empty, stop
        if [p for p in path.iterdir() if p.name != '.DS_Store']:
            return

        # otherwise, remove it
        shutil.rmtree(str(path), ignore_errors=True)
        prune_empty(path.parent)


def get_permission(*question):
    question = ' '.join(question)
    if not question.endswith((' ', '\n')):
        question += ' '
    response = input(question)
    while True:
        response = response.lower()
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        else:
            response = input('Please enter y[es]|n[o]')


def cmd(args, fail_ok=False, cwd=None, quiet=False):
    process = subprocess.Popen(
        args,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        cwd=cwd,
        universal_newlines=True)
    stdout, stderr = process.communicate(timeout=1)
    if stderr and not fail_ok:
        _exit(
            "Command `{}` failed: {}".format(' '.join(args), stderr),
            quiet=quiet)
    else:
        return stdout.strip()


def dirty_repo(quiet=False):
    return cmd('git status --porcelain'.split(), quiet=quiet) is not ''


def _print(*msg, quiet=False):
    if not quiet:
        print(*msg)


def _exit(*msg, quiet=False):
    _print(*msg, quiet=quiet)
    exit()


def last_commit(quiet=False):
    try:
        return cmd('git rev-parse HEAD'.split())
    except OSError:
        if not quiet:
            print(
                'Could not detect last commit. Perhaps you have not committed yet?'
            )
        exit()


def string_from_vim(prompt, string=None):
    if string is None:
        string = ' '
    path = Path('/', 'tmp', datetime.now().strftime('%s') + '.txt')
    delimiter = '\n' + '-' * len(prompt.split('\n')[-1]) + '\n'
    with path.open('w') as f:
        f.write(prompt + delimiter + string)
    start_line = 3 + prompt.count('\n')
    subprocess.call('vim +{} {}'.format(start_line, path), shell=True)
    with path.open() as f:
        file_contents = f.read()[:-1]
        if delimiter not in file_contents:
            raise RuntimeError("Don't delete the delimiter.")
        prompt, string = file_contents.split(delimiter)
    path.unlink()
    return string


def generate_runs(path: str, flags: List[str]):
    flag_combinations = list(itertools.product(*flags))
    for flags in flag_combinations:
        if len(flag_combinations) > 1:
            path += '_' + '_'.join(f.lstrip('-') for f in flags)
        yield path, flags
    if not flag_combinations:
        yield path, []


PATH = 'path'
ROOT_PATH = '.'
SEP = '/'
MAIN = 'main'
DEFAULT = 'DEFAULT'
NAME = 'name'
PATTERN = 'pattern'
NEW = 'new'
REMOVE = 'rm'
MOVE = 'mv'
LOOKUP = 'lookup'
LIST = 'ls'
FLAGS = 'flags'
TABLE = 'table'
REPRODUCE = 'reproduce'
COMMAND = 'command'
COMMIT = 'commit'
DESCRIPTION = 'description'
CHDESCRIPTION = 'change-description'
KILLALL = 'killall'
