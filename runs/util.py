import argparse
import codecs
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path, PurePath
from typing import List

RED = "\033[1;31m"
BLUE = "\033[1;34m"
CYAN = "\033[1;36m"
GREEN = "\033[0;32m"
RESET = "\033[0;0m"
BOLD = "\033[;1m"
REVERSE = "\033[;7m"


def highlight(*args, sep=' '):
    return GREEN + sep.join(map(str, args)) + RESET


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

def chunks(it, size):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(it), size):
        yield it[i:i + size]

def string_from_vim(prompt: str, string=None, line_length=100):
    if string is None:
        string = ' '
    path = Path('/', 'tmp', datetime.now().strftime('%s') + '.txt')
    prompt = '\n'.join(chunks(prompt.strip('\n '), line_length))
    delimiter = '\n' + '=' * line_length
    with path.open('w') as f:
        f.write(prompt + delimiter + '\n' + string.lstrip('\n'))
    start_line = 3 + prompt.count('\n')
    subprocess.call('vim +{} {}'.format(start_line, path), shell=True)
    with path.open() as f:
        file_contents = f.read()[:-1]
        if delimiter not in file_contents:
            raise RuntimeError("Don't delete the delimiter.")
        prompt, string = file_contents.split(delimiter)
    path.unlink()
    return string


def nonempty_string_type(value):
    if value == '' or not isinstance(value, str):
        raise argparse.ArgumentTypeError("Value must be a nonempty string.")
    return value


def pure_path_list(paths: str) -> List[PurePath]:
    return [PurePath(path) for path in paths.split()]


def comma_sep_list(string: str) -> List[str]:
    return string.split(',')


def space_sep_list(string: str) -> List[str]:
    return string.split()


def flag_list(flags_string: str) -> List[List[str]]:
    if flags_string:
        flags = codecs.decode(
            flags_string, encoding='unicode_escape').strip('\n').split('\n')
    else:
        flags = []
    flag_list = []
    for flag in flags:
        if re.match('--[^=]*=.*', flag):
            key, values = flag.split('=')
            flag_list.append(tuple((key + '=' + value for value in values.split('|'))))
        elif re.match('--[^=]* .*', flag):
            key, values = flag.split(' ')
            flag_list.append(tuple((key + ' ' + value for value in values.split('|'))))
        else:
            flag_list.append((flag, ))
    return flag_list
