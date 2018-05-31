import argparse
import itertools
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List

from termcolor import colored


def get_permission(self, *question):
    if self.assume_yes:
        return True
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


def highlight(*args):
    string = ' '.join(map(str, args))
    return colored(string, color='blue', attrs=['bold'])


def find_up(filename):
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


def nonempty_string(value):
    if value == '' or not isinstance(value, str):
        raise argparse.ArgumentTypeError("Value must be a nonempty string.")
    return value
