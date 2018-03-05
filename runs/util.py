import os
import pprint
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml
from anytree import RenderTree
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


def get_permission(question):
    if not question.endswith(' '):
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


def cmd(args, fail_ok=False, cwd=None):
    process = subprocess.Popen(args,
                               stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               cwd=cwd,
                               universal_newlines=True)
    stdout, stderr = process.communicate(timeout=1)
    if stderr and not fail_ok:
        raise OSError("Command `{}` failed: {}".format(args, stderr))
    else:
        return stdout.strip()


def dirty_repo():
    return cmd('git status --porcelain'.split()) is not ''


def last_commit():
    try:
        return cmd('git rev-parse HEAD'.split())
    except OSError:
        print('Could not detect last commit. Perhaps you have not committed yet?')
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


FILESYSTEM = 'filesystem'
NAME = 'name'
PATTERN = 'pattern'
NEW = 'new'
REMOVE = 'rm'
MOVE = 'mv'
LOOKUP = 'lookup'
LIST = 'ls'
TABLE = 'table'
REPRODUCE = 'reproduce'
COMMAND = 'command'
COMMIT = 'commit'
DESCRIPTION = 'description'
CHDESCRIPTION = 'chdesc'

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
