# stdlib
import argparse
from datetime import datetime
from pathlib import Path, PurePath
import re
import shutil
import subprocess

RED = "\033[1;31m"
BLUE = "\033[1;34m"
CYAN = "\033[1;36m"
GREEN = "\033[0;32m"
RESET = "\033[0;0m"
BOLD = "\033[;1m"
REVERSE = "\033[;7m"


def highlight(*args, sep=' '):
    return GREEN + sep.join(map(str, args)) + RESET


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


def interpolate_keywords(path, string):
    keywords = dict(path=path, name=PurePath(path).name)
    for word, replacement in keywords.items():
        string = string.replace(f'<{word}>', str(replacement))
    return string


def natural_order(text):
    return [int(c) if c.isdigit() else c for c in re.split('(\d+)', text)]
