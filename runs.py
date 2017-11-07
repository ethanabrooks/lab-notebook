#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import sys
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from getpass import getpass

import libtmux
import yaml
from git import Repo
from paramiko import SSHException
from paramiko.client import SSHClient, AutoAddPolicy
from tabulate import tabulate
from termcolor import colored

if sys.version_info.major == 2:
    FileNotFoundError = OSError

BUFFSIZE = 1024


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
    for path in run_paths(run_name, runs_dir):
        dirname = os.path.dirname(path)
        os.makedirs(dirname, exist_ok=True)


def run_paths(run_name, runs_dir):
    return [os.path.join(runs_dir, name, run_name + ext)
            for name, ext in [('tensorboard', '/'),
                              ('checkpoints', '.ckpt')]]


def build_flags(name, runs_dir, tb_dir_flag, save_path_flag):
    tb_dir, save_path = run_paths(name, runs_dir)
    return ' '.join([
        '{}={}'.format(flag, value)
        for flag, value in [(tb_dir_flag, tb_dir), (save_path_flag, save_path)]
        if flag is not None])


def build_command(command, name, runs_dir, virtualenv_path, tb_dir_flag, save_path_flag):
    command += ' ' + build_flags(name, runs_dir, tb_dir_flag, save_path_flag)
    if virtualenv_path:
        return 'source ' + virtualenv_path + '/bin/activate; ' + command
    return command


def run_tmux(name, window_name, command):
    server = libtmux.Server()
    server.new_session(name, kill_session=True)
    session = server.find_where(
        dict(session_name=name))  # type: libtmux.Session
    pane = session.new_window(window_name).attached_pane
    pane.send_keys(command)


def new(name, command, description, virtualenv_path, overwrite, runs_dir, db_filename,
        tb_dir_flag, save_path_flag):
    assert '.' not in name
    now = datetime.now()

    # deal with collisions
    db_path = os.path.join(runs_dir, db_filename)
    if name in load(db_path):
        if overwrite:
            delete_run(name, db_filename, runs_dir)
        else:
            name += now.strftime('%s')

    make_dirs(name, runs_dir)
    repo = Repo()
    if repo.is_dirty():
        raise RuntimeError("Repo is dirty. You should commit before run.")

    command = build_command(command, name, runs_dir, virtualenv_path, tb_dir_flag, save_path_flag)

    last_commit = next(repo.iter_commits())
    if description is None:
        description = last_commit.message
    entry = dict(
        command=command,
        commit=last_commit.hexsha,
        datetime=now.isoformat(),
        description=description,
    )

    with RunDB(path=db_path) as db:
        db[name] = entry

    run_tmux(name, description, command)

    print('Command sent to session:')
    print(code_format(command))
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
        for path in run_paths(name, runs_dir):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                try:
                    os.remove(path)
                except FileNotFoundError as e:
                    print(colored(e.strerror + ': ' + path, color='yellow'))

        server = libtmux.Server()
        session = server.find_where(
            dict(session_name=name))  # type: libtmux.Session
        if session:
            session.kill_session()


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


def get_table_from_path(db_path, column_width, host, username, pattern=None):
    db = load(db_path, host, username)
    if pattern:
        db = filter_by_regex(db, pattern)
    return get_table(db, column_width)


def get_table(db, column_width):
    def get_values(entry, key):
        try:
            value = str(entry[key])
            if len(value) > column_width:
                value = value[:column_width] + '...'
            return value
        except KeyError:
            return '_'

    headers = sorted(set(key for _, entry in db.items() for key in entry))
    table = [[name] + [get_values(entry, key) for key in headers]
             for name, entry in db.items()]
    headers = [NAME] + list(headers)
    return tabulate(table, headers=headers)


def reproduce(runs_dir, db_filename, name):
    db = load(os.path.join(runs_dir, db_filename))
    commit = lookup(db, name, key='commit')
    command = lookup(db, name, key='command')
    description = lookup(db, name, key=DESCRIPTION)
    print('To reproduce:\n',
          code_format('git checkout {}\n'.format(commit)),
          code_format("runs new {} '{}' --description='{}'".format(
              name, command, description)))


class Config:
    def __init__(self, runsrc_path):
        self.runs_dir = '.runs/'
        self.db_filename = '.runs.yml'
        self.tb_dir_flag = '--tb-dir'
        self.save_path_flag = '--save-path'
        self.column_width = 30
        self.virtualenv_path = None
        try:
            with open(runsrc_path) as f:
                print('Config file loaded from', runsrc_path)
                for k, v in yaml.load(f).items():
                    if v == 'None':
                        v = None
                    self.__setattr__(k, v)
        except FileNotFoundError:
            pass

    def update_with_args(self, args):
        for k, v in vars(args).items():
            if v is not None:
                self.__setattr__(k.replace('-', '_'), v)


DEST = 'dest'
NAME = 'name'
PATTERN = 'pattern'
DESCRIPTION = 'description'
DEFAULT_RUNS_DIR = '.runs'

NEW = 'new'
DELETE = 'delete'
LOOKUP = 'lookup'
LIST = 'list'
TABLE = 'table'
REPRODUCE = 'reproduce'


def main():
    config = Config('.runsrc')

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

    subparsers = parser.add_subparsers(dest=DEST)

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
    new_parser.add_argument('--save_path_flag', default=config.save_path_flag,
                            help='Flag to pass to program to specify '
                                 'tensorboard directory.')
    new_parser.add_argument('--virtualenv-path', default=None, help=virtualenv_path_help)
    new_parser.add_argument('--overwrite', action='store_true', help='If this flag is given, this entry will '
                                                                     'overwrite any entry with the same name. '
                                                                     'Otherwise, a timestamp will be appended to any '
                                                                     'new name that is already in the database.')
    new_parser.add_argument('--description', help='Description of this run. Write whatever you want.')

    delete_parser = subparsers.add_parser(DELETE, help="Delete runs from the database (and all associated tensorboard "
                                                       "and checkpoint files). Don't worry, the script will ask for "
                                                       "confirmation before deleting anything.")
    delete_parser.add_argument(PATTERN, help='This script will only delete entries in the database whose names are a '
                                             'complete (not partial) match of this regex pattern.')

    pattern_help = 'Only display names matching this pattern.'

    list_parser = subparsers.add_parser(LIST, help='List all names in run database.')
    list_parser.add_argument('--' + PATTERN, default=None, help=pattern_help)

    table_parser = subparsers.add_parser(TABLE, help='Display contents of run database as a table.')
    table_parser.add_argument('--' + PATTERN, default=None, help=pattern_help)
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
    reproduce_parser.add_argument('--overwrite', action='store_true', help='If this flag is provided, the reproducing '
                                                                           'run will overwrite the reproduced run.')

    args = parser.parse_args()
    config.update_with_args(args)

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
            overwrite=args.overwrite,
            runs_dir=config.runs_dir,
            db_filename=config.db_filename,
            tb_dir_flag=config.tb_dir_flag,
            save_path_flag=config.save_path_flag)

    elif args.dest == DELETE:
        assert args.host is None, 'SSH into remote before calling runs delete.'
        delete(args.pattern, config.db_filename, config.runs_dir)

    elif args.dest == LIST:
        for name in db:
            print(name)

    elif args.dest == TABLE:
        print(get_table_from_path(db_path,
                                  config.column_width,
                                  args.host,
                                  args.username,
                                  args.pattern))

    elif args.dest == LOOKUP:
        print(lookup(db, args.name, args.key))

    elif args.dest == REPRODUCE:
        reproduce(config.runs_dir, config.db_filename, args.name)

    else:
        raise RuntimeError("'{}' is not a supported dest.".format(args.dest))


if __name__ == '__main__':
    main()
