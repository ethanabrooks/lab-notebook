import os
import pprint
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import itertools
import yaml
from anytree import NodeMixin, RenderTree
from termcolor import colored

if sys.version_info.major == 2:
    pass
else:
    FileNotFoundError = OSError


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


def prune_leaves(node: Optional[NodeMixin]):
    # if the node has children or is a run node, terminate
    if node is None or node.children:
        return node

    parent = node.parent
    node.parent = None
    prune_leaves(parent)


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


def is_run_node(node):
    assert isinstance(node, NodeMixin)
    return hasattr(node, COMMIT)


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


def move(dest, kill_tmux, assume_yes):
    multi_move = len(self.nodes()) > 1

    if dest.is_run() and multi_move:
        _exit(
            "'{}' already exists and '{}' matches the following runs:\n"
            "{}\n"
            "Cannot move multiple runs into an existing run.".format(
                dest, self.path, '\n'.join(self.paths)))

    def marshall_moves(src_node, dest_route):
        """ Collect moves corresponding to a src node and a dest route """
        assert isinstance(src_node, NodeMixin)

        existing_dir = dest.exists and not dest.is_run()
        non_existing_dir = not dest.exists and (dest.dir_path
                                                or multi_move)
        if existing_dir or non_existing_dir:
            # put the current node into dest
            dest_route = DBPath(dest_route.parts + [src_node.path[-1]])

        def dest_run(src_base, src_run):
            stem = src_run.path[len(src_base.path):]
            return Run(dest_route.parts + list(stem))

        # add child runs to moves list
        return [(Run(src_run_node), dest_run(src_node, src_run_node))
                for src_run_node in findall(src_node, is_run_node)]

    moves = [(s, d) for node in self.nodes()
             for s, d in marshall_moves(node, dest)]

    # check before moving
    prompt = ("Planned moves:\n\n" + '\n'.join(s.path + ' -> ' + d.path
                                               for s, d in moves) +
              '\n\nContinue?')

    if moves and (assume_yes or get_permission(prompt)):

        # check for conflicts with existing runs
        already_exists = [
            d for s, d in moves if d.is_run() and s.path != d.path
            ]
        if already_exists:
            prompt = 'Runs to be removed:\n{}\nContinue?'.format(
                '\n'.join(map(str, already_exists)))
            if not (assume_yes or get_permission(prompt)):
                self.exit()

        for src, dest in moves:
            if dest.is_run() and src.path != dest.path:
                dest.remove()
            if src.path != dest.path:
                src.move(dest, kill_tmux)


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

# @contextmanager
# def read_remote_file(remote_filename, host, username):
#     client = SSHClient()
#     client.set_missing_host_key_policy(AutoAddPolicy())
#     try:
#         client.connect(host, username=username, look_for_keys=True)
#     except SSHException:
#         client.connect(host,
#                        username=username,
#                        password=getpass("Enter password:"),
#                        look_for_keys=False)
#     if not client:
#         raise RuntimeError("Connection not opened.")
#
#     sftp = client.open_sftp()
#     try:
#         sftp.stat(remote_filename)
#     except Exception:
#         raise RuntimeError('There was a problem accessing', remote_filename)
#
#     with sftp.open(remote_filename) as f:
#         yield f
