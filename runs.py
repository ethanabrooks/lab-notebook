#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import sys
from contextlib import contextmanager
import subprocess
from datetime import datetime
from getpass import getpass

import yaml
from paramiko import SSHException
from paramiko.client import SSHClient, AutoAddPolicy
from tabulate import tabulate
from termcolor import colored

if sys.version_info.major == 2:
    FileNotFoundError = OSError

BUFFSIZE = 1024

INPUT_COMMAND = 'input-command'
COMMAND = 'command'
COMMIT = 'commit'
DATETIME = 'datetime'
DESCRIPTION = 'description'


def code_format(*args):
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


def make_dirs(run_name, runs_dir):
    for run_dir in run_dirs(run_name, runs_dir):
        os.makedirs(run_dir, exist_ok=True)


def run_dirs(run_name, runs_dir):
    return [os.path.join(runs_dir, 'tensorboard', run_name),
            os.path.join(runs_dir, 'checkpoints', run_name)]


def run_paths(run_name, runs_dir):
    """
    Note that the `dirname` of each of these gets deleted by `delete_run`.
    Make sure that dir contains only files from that run.
    """
    dirs = run_dirs(run_name, runs_dir)
    files = '', 'model.ckpt'
    assert len(dirs) == len(files)
    return [os.path.join(run_dir, run_file) for run_dir, run_file in zip(dirs, files)]


def build_flags(name, runs_dir, tb_dir_flag, save_path_flag, extra_flags):
    tb_dir, save_path = run_paths(name, runs_dir)
    flags = [(tb_dir_flag, tb_dir), (save_path_flag, save_path)]
    for flag, value in extra_flags:
        value = value.replace('<run-name>', name).replace('<runs-dir>', runs_dir)
        flags += [(flag, value)]

    return ' '.join([
                        '{}={}'.format(flag, value)
                        for flag, value in flags
                        if flag is not None])


def build_command(command, name, runs_dir, virtualenv_path, tb_dir_flag, save_path_flag, extra_flags):
    command += ' ' + build_flags(name, runs_dir, tb_dir_flag, save_path_flag, extra_flags)
    if virtualenv_path:
        return 'source ' + virtualenv_path + '/bin/activate; ' + command
    return command


def run_tmux(name, window_name, main_cmd):
    kill_tmux(name)
    subprocess.check_call('tmux new -d -s'.split() + [name, '-n', window_name])
    cd_cmd = 'cd ' + os.path.realpath(os.path.curdir)
    for cmd in [cd_cmd, main_cmd]:
        subprocess.check_call(
            'tmux send-keys -t'.split() + [name, cmd, 'Enter']
        )


def kill_tmux(name):
    subprocess.call('tmux kill-session -t'.split() + [name])


def rename_tmux(old_name, new_name):
    subprocess.call('tmux rename-session -t'.split() + [old_name, new_name])


def cmd(string):
    return subprocess.check_output(string.split(), universal_newlines=True)


def new(name, command, description, virtualenv_path, overwrite, runs_dir, db_filename,
        tb_dir_flag, save_path_flag, extra_flags):
    for char in '.&':
        assert char not in name, 'run name cannot include "{}"'.format(char)
    now = datetime.now()

    # deal with collisions
    db_path = os.path.join(runs_dir, db_filename)
    if name in load(db_path):
        if overwrite:
            delete_run(name, db_filename, runs_dir)
        else:
            name += now.strftime('%s')

    make_dirs(name, runs_dir)
    if cmd('git status --porcelain') is not '':
        if not get_yes_or_no("Repo is dirty. You should commit before run. Run anyway?"):
            exit()

    processed_command = build_command(command, name, runs_dir, virtualenv_path,
                                      tb_dir_flag, save_path_flag, extra_flags)

    if description is None:
        description = cmd('git log -1 --pretty=%B')

    last_commit_hex = cmd('git rev-parse HEAD')
    entry = {
        INPUT_COMMAND: command,
        COMMAND: processed_command,
        COMMIT: last_commit_hex,
        DATETIME: now.isoformat(),
        DESCRIPTION: description,
    }

    with RunDB(path=db_path) as db:
        db[name] = entry

    run_tmux(name, description, processed_command)

    print('Command sent to session:')
    print(code_format(processed_command))
    print('List active:')
    print(code_format('tmux list-session'))
    print('Attach:')
    print(code_format('tmux attach -t', name))


def filter_by_regex(db, pattern):
    return {key: db[key] for key in db
            if re.match('^' + pattern + '$', key) is not None}


def delete_run(name, db_filename, runs_dir):
    print('Deleting {}...'.format(name))
    with RunDB(path=(os.path.join(runs_dir, db_filename))) as db:
        del db[name]
        for run_dir in run_dirs(name, runs_dir):
            shutil.rmtree(run_dir)

    kill_tmux(name)


def rename(old_name, new_name, db_filename, runs_dir):
    with RunDB(path=(os.path.join(runs_dir, db_filename))) as db:
        db[new_name] = db[old_name]
        del db[old_name]

        for old_dir, new_dir in zip(run_dirs(old_name, runs_dir),
                                    run_dirs(new_name, runs_dir)):
            os.rename(old_dir, new_dir)

    rename_tmux(old_name, new_name)


def delete(pattern, db_filename, runs_dir):
    db_path = os.path.join(runs_dir, db_filename)
    filtered = filter_by_regex(load(db_path), pattern)
    if filtered:
        question = 'Delete the following runs?\n' + '\n'.join(filtered) + '\n'
        if get_yes_or_no(question):
            for run_name in filtered:
                delete_run(run_name, db_filename, runs_dir)
                print('Deleted', run_name)
    else:
        print('No runs match pattern. Recorded runs:')
        for name in load(db_path):
            print(name)


def lookup(db, name, key):
    documented_runs_message = "Documented runs are {}.".format(name, db.keys())
    if key is None:
        return documented_runs_message
    if name not in db.keys():
        raise KeyError(
            "`{}` is not a documented run." + documented_runs_message)
    entry = db[name]
    if key not in entry:
        raise KeyError(
            "`{}` not a valid key. Valid keys are {}.".format(
                key, entry.keys()))
    return entry[key]


def get_table_from_path(db_path, column_width, host, username, hidden_columns, pattern=None):
    db = load(db_path, host, username)
    if pattern:
        db = filter_by_regex(db, pattern)
    return get_table(db, column_width, hidden_columns)


def get_table(db, column_width, hidden_columns):
    def get_values(entry, key):
        try:
            value = str(entry[key])
            if len(value) > column_width:
                value = value[:column_width] + '...'
            return value
        except KeyError:
            return '_'

    headers = sorted(set(key for _, entry in db.items() for key in entry) - set(hidden_columns))
    table = [[name] + [get_values(entry, key) for key in headers]
             for name, entry in sorted(db.items())]
    headers = [NAME] + list(headers)
    return tabulate(table, headers=headers)


def reproduce(runs_dir, db_filename, name):
    db = load(os.path.join(runs_dir, db_filename))
    commit = lookup(db, name, key=COMMIT)
    command = lookup(db, name, key=INPUT_COMMAND)
    description = lookup(db, name, key=DESCRIPTION)
    print('To reproduce:\n',
          code_format('git checkout {}\n'.format(commit)),
          code_format("runs new {} '{}' --description='{}'".format(
              name, command, description)))


class Config:
    def __init__(self, root):
        self.runs_dir = os.path.join(root, '.runs/')
        self.db_filename = os.path.join(root, '.runs.yml')
        self.tb_dir_flag = '--tb-dir'
        self.save_path_flag = '--save-path'
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
RENAME = 'rename'
LOOKUP = 'lookup'
LIST = 'list'
TABLE = 'table'
REPRODUCE = 'reproduce'


def main():
    runsrc_file = find_file_backward('.runsrc')
    if runsrc_file is None:
        config = Config(root='.')
    else:
        config = Config(root=os.path.dirname(runsrc_file))
        # load values from config
        with open(runsrc_file) as f:
            print('Config file loaded.')
            for k, v in yaml.load(f).items():

                # Don't treat None like a string
                if v == 'None':
                    v = eval(v)

                config.setattr(k, v)

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=None,
                        help='IP address or hostname (without username). Used for accessing '
                             'database on remote server.')
    parser.add_argument('--username', default=None,
                        help='Username associated with remote host. Used for accessing '
                             'database on remote server.')
    parser.add_argument('--runs_dir', default=config.runs_dir, help='Custom path to directory containing runs '
                                                                    'database (default, `runs.yml`). Should not '
                                                                    'need to be specified for local runs but '
                                                                    'probably required for accessing databses '
                                                                    'remotely.')
    parser.add_argument('--db_filename', default=config.db_filename,
                        help='Name of YAML file storing run database information.')

    subparsers = parser.add_subparsers(dest='dest')

    virtualenv_path_help = 'Path to virtual environment, if one is being ' \
                           'used. If not `None`, the program will source ' \
                           '`<virtualenv-path>/bin/activate`.'

    new_parser = subparsers.add_parser(NEW, help='Start a new run.')
    new_parser.add_argument(NAME, help='Unique name assigned to new run.')
    new_parser.add_argument('command', help='Command to run to start tensorflow program. Do not include the `--tb-dir` '
                                            'or `--save-path` flag in this argument')
    new_parser.add_argument('--tb-dir-flag', default=config.tb_dir_flag,
                            help='Flag to pass to program to specify tensorboard '
                                 'directory.')
    new_parser.add_argument('--save-path-flag', default=config.save_path_flag,
                            help='Flag to pass to program to specify '
                                 'tensorboard directory.')
    new_parser.add_argument('--virtualenv-path', default=None, help=virtualenv_path_help)
    new_parser.add_argument('--no-overwrite', action='store_true', help='If this flag is given, a timestamp will be '
                                                                        'appended to any new name that is already in '
                                                                        'the database.  Otherwise this entry will '
                                                                        'overwrite any entry with the same name. ')
    new_parser.add_argument('--description', help='Description of this run. Write whatever you want.')

    delete_parser = subparsers.add_parser(DELETE, help="Delete runs from the database (and all associated tensorboard "
                                                       "and checkpoint files). Don't worry, the script will ask for "
                                                       "confirmation before deleting anything.")
    delete_parser.add_argument(PATTERN, help='This script will only delete entries in the database whose names are a '
                                             'complete (not partial) match of this regex pattern.')

    rename_parser = subparsers.add_parser(RENAME, help='Lookup specific value associated with database entry')
    rename_parser.add_argument('old', help='Name of run to rename.')
    rename_parser.add_argument('new', help='New name for run')

    pattern_help = 'Only display names matching this pattern.'

    list_parser = subparsers.add_parser(LIST, help='List all names in run database.')
    list_parser.add_argument('--' + PATTERN, default=None, help=pattern_help)

    table_parser = subparsers.add_parser(TABLE, help='Display contents of run database as a table.')
    table_parser.add_argument('--' + PATTERN, default=None, help=pattern_help)
    table_parser.add_argument('--hidden-columns', default='input-command',
                              help='Comma-separated list of columns to not display in table.')
    table_parser.add_argument('--column-width', type=int, default=config.column_width,
                              help='Maximum width of table columns. Longer '
                                   'values will be truncated and appended '
                                   'with "...".')

    lookup_parser = subparsers.add_parser(LOOKUP, help='Lookup specific value associated with database entry')
    lookup_parser.add_argument(NAME, help='Name of run that value is associated with.')
    lookup_parser.add_argument('key', help='Key that value is associated with. To view all available keys, '
                                           'use `--key=None`.')

    reproduce_parser = subparsers.add_parser(
        REPRODUCE, help='Print commands to reproduce a run.')
    reproduce_parser.add_argument(NAME)
    reproduce_parser.add_argument('--description', type=str, default=None, help='Description to be assigned to new '
                                                                                'run. If None, use the same '
                                                                                'description as the run being '
                                                                                'reproduced.')
    reproduce_parser.add_argument('--virtualenv-path', default=None, help=virtualenv_path_help)
    reproduce_parser.add_argument('--no-overwrite', action='store_true',
                                  help='If this flag is given, a timestamp will be '
                                       'appended to any new name that is already in '
                                       'the database.  Otherwise this entry will '
                                       'overwrite any entry with the same name. ')

    args = parser.parse_args()

    for k, v in vars(args).items():
        if v is not None:  # None indicates that the flag was not set by the user.
            config.setattr(k, v)

    db_path = os.path.join(config.runs_dir, config.db_filename)
    db = load(db_path, host=args.host, username=args.username)
    if hasattr(config, PATTERN) and args.pattern is not None:
        db = filter_by_regex(db, args.pattern)
    if config.runs_dir is DEFAULT_RUNS_DIR and args.host is not None:
        print(colored('Using default path to runs_dir: "{}". '
                      'When accessing remote files, you may want to '
                      'specify the complete path.'.format(DEFAULT_RUNS_DIR),
                      color='red'))
    if args.dest == NEW:
        assert args.host is None, 'SSH into remote before calling runs new.'
        new(name=args.name,
            description=args.description,
            virtualenv_path=config.virtualenv_path,
            command=args.command,
            overwrite=not args.no_overwrite,
            runs_dir=config.runs_dir,
            db_filename=config.db_filename,
            tb_dir_flag=config.tb_dir_flag,
            save_path_flag=config.save_path_flag,
            extra_flags=config.extra_flags)

    elif args.dest == DELETE:
        assert args.host is None, 'SSH into remote before calling runs delete.'
        delete(args.pattern, config.db_filename, config.runs_dir)

    elif args.dest == RENAME:
        rename(args.old, args.new, config.db_filename, config.runs_dir)

    elif args.dest == LIST:
        for name in db:
            print(name)

    elif args.dest == TABLE:
        hidden_columns = args.hidden_columns.split(',')
        print(get_table_from_path(db_path,
                                  config.column_width,
                                  args.host,
                                  args.username,
                                  hidden_columns,
                                  pattern=args.pattern))

    elif args.dest == LOOKUP:
        print(lookup(db, args.name, args.key))

    elif args.dest == REPRODUCE:
        reproduce(config.runs_dir, config.db_filename, args.name)

    else:
        raise RuntimeError("'{}' is not a supported dest.".format(args.dest))


if __name__ == '__main__':
    main()
