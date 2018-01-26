import fnmatch
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime
from getpass import getpass

import yaml
from paramiko import SSHClient, AutoAddPolicy, SSHException
from termcolor import colored

if sys.version_info.major == 2:
    pass
else:
    FileNotFoundError = OSError


def highlight(*args):
    string = ' '.join(map(str, args))
    return colored(string, color='blue', attrs=['bold'])


def load(path, host=None, username=None):
    try:
        if host:
            with read_remote_file(path, host, username) as f:
                return yaml.load(f)
        else:
            with open(path, 'r') as f:
                return yaml.load(f)
    except FileNotFoundError:
        return dict()


def dump(db, path):
    with open(path, 'w') as f:
        yaml.dump(db, f, default_flow_style=False)


class RunDB:
    def __init__(self, path):
        self._path = path
        self._db = None

    def __enter__(self):
        self._db = load(self._path)
        return self._db

    def __exit__(self, exc_type, exc_val, exc_tb):
        dump(self._db, self._path)
        self._db = None


@contextmanager
def read_remote_file(remote_filename, host, username):
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    try:
        client.connect(host, username=username, look_for_keys=True)
    except SSHException:
        client.connect(host,
                       username=username,
                       password=getpass("Enter password:"),
                       look_for_keys=False)
    if not client:
        raise RuntimeError("Connection not opened.")

    sftp = client.open_sftp()
    try:
        sftp.stat(remote_filename)
    except Exception:
        raise RuntimeError('There was a problem accessing', remote_filename)

    with sftp.open(remote_filename) as f:
        yield f


def find_file_backward(filename):
    filepath = filename
    while os.path.dirname(os.path.abspath(filepath)) is not '/':
        if os.path.exists(filepath):
            return filepath
        filepath = os.path.join(os.path.pardir, filepath)


def get_yes_or_no(question):
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


def run_dirs(runs_dir, run_name):
    return [os.path.join(runs_dir, 'tensorboard', run_name),
            os.path.join(runs_dir, 'checkpoints', run_name)]


def run_paths(runs_dir, run_name):
    """
    Note that the `dirname` of each of these gets deleted by `delete_run`.
    Make sure that dir contains only files from that run.
    """
    dirs = run_dirs(runs_dir, run_name)
    files = '', 'model.ckpt'
    assert len(dirs) == len(files)
    return [os.path.join(run_dir, run_file) for run_dir, run_file in zip(dirs, files)]


def make_dirs(runs_dir, run_name):
    for run_dir in run_dirs(runs_dir, run_name):
        os.makedirs(run_dir, exist_ok=True)


def cmd(string, fail_ok=False):
    args = string.split()
    if fail_ok:
        return subprocess.call(args)
    else:
        return subprocess.check_output(args, universal_newlines=True)


def run_tmux(name, window_name, main_cmd):
    kill_tmux(name)
    subprocess.check_call('tmux new -d -s'.split() + [name, '-n', window_name])
    cd_cmd = 'cd ' + os.path.realpath(os.path.curdir)
    for command in [cd_cmd, main_cmd]:
        cmd('tmux send-keys -t ' + name + ' ' + command + 'Enter')


def kill_tmux(name):
    cmd('tmux kill-session -t ' + name, fail_ok=True)


def rename_tmux(old_name, new_name):
    cmd('tmux rename-session -t ' + old_name + ' ' + new_name)


def filter_by_pattern(db, pattern, regex):
    def match(string):
        if regex:
            return re.match('^' + pattern + '$', string) is not None
        else:
            return fnmatch.fnmatch(string, pattern)

    return {k: v for k, v in db.items() if match(k)}


def split_pattern(runs_dir, pattern):
    *subdir, pattern = pattern.split('/')
    return os.path.join(runs_dir, *subdir), pattern


def collect_runs(runs_dir, pattern, db_filename, regex):
    if pattern is None:
        return runs_dir, load(os.path.join(runs_dir, db_filename))
    else:
        runs_dir, pattern = split_pattern(runs_dir, pattern)
        db = load(os.path.join(runs_dir, db_filename))
        filtered = filter_by_pattern(db, pattern, regex)
        return runs_dir, list(filtered.keys())


def no_match(runs_dir, db_filename):
    print('No runs match pattern. Recorded runs:')
    for name in load(os.path.join(runs_dir, db_filename)):
        print(name)


def string_from_vim(prompt, string=''):
    path = os.path.join('/', 'tmp', datetime.now().strftime('%s') + '.txt')
    delimiter = '\n' + '-' * len(prompt.split('\n')[-1]) + '\n'
    with open(path, 'w') as f:
        f.write(prompt + delimiter + string)
    start_line = 3 + prompt.count('\n')
    os.system('vim +{} {}'.format(start_line, path))
    with open(path) as f:
        file_contents = f.read()[:-1]
        if delimiter not in file_contents:
            raise RuntimeError("Don't delete the delimiter.")
        prompt, string = file_contents.split(delimiter)
    os.remove(path)
    return string


class Config:
    def __init__(self, root):
        self.runs_dir = os.path.join(root, '.runs/')
        self.db_filename = 'runs.yml'
        self.tb_dir_flag = '--tb-dir'
        self.save_path_flag = '--save-path'
        self.save_path_flag = '--save-path'
        self.regex = False
        self.column_width = 30
        self.virtualenv_path = None
        self.extra_flags = []

    def setattr(self, k, v):
        setattr(self, k.replace('-', '_'), v)


NAME = 'name'
PATTERN = 'pattern'
DEFAULT_RUNS_DIR = '.runs'
NEW = 'new'
DELETE = 'delete'
MOVE = 'move'
LOOKUP = 'lookup'
LIST = 'list'
TABLE = 'table'
REPRODUCE = 'reproduce'
BUFFSIZE = 1024
INPUT_COMMAND = 'input-command'
COMMAND = 'command'
COMMIT = 'commit'
DATETIME = 'datetime'
DESCRIPTION = 'description'
