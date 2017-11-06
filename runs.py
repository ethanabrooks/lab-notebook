#!/usr/bin/env python
import argparse
import socket
from contextlib import contextmanager
from datetime import datetime
from getpass import getpass

import libtmux
import os
import re
import shutil
import visualizer
import yaml
from copy import deepcopy
from git import Repo
from paramiko import SSHException
from paramiko.client import SSHClient, AutoAddPolicy
from tabulate import tabulate
from termcolor import colored

DEST = 'dest'
RUNS = '.runs'
NAME = 'name'
COMMAND = 'command'
DATETIME = 'datetime'
TB_DIR = 'tb-dir'
GOAL_LOG_FILE = 'goal-log-file'
SAVE_PATH = 'save-path'
RECORDS = 'records'
PATTERN = 'pattern'
PORT = 'port'
COMMIT = 'commit'
DESCRIPTION = 'description'
DEFAULT_RUNS_DIR = '.runs'

NEW = 'new'
SAVE = 'save'
DELETE = 'delete'
LOOKUP = 'lookup'
LIST = 'list'
TABLE = 'table'
REPRODUCE = 'reproduce'
VISUALIZE = 'visualize'

BUFFSIZE = 1024


def code_format(*args):
    string = ' '.join(map(str, args))
    return colored(string, color='blue', attrs=['bold'])


# IO

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
    # print("Connecting to server.")
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


def run_paths(run_name, runs_dir):
    def build_path(name, ext):
        return os.path.join(runs_dir, name, run_name + ext)

    return {'tb-dir': build_path('tensorboard', '/'),
            'save-path': build_path('checkpoints', '.ckpt'),
            'goal-log-file': build_path('goal-logs', '.logs')}


def make_dirs(run_name, runs_dir):
    for path in run_paths(run_name, runs_dir).values():
        dirname = os.path.dirname(path)
        os.makedirs(dirname, exist_ok=True)


def choose_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for port in range(8000, 9999):
        try:
            sock.bind(('', port))
            sock.close()
            return port
        except OSError:
            pass


def build_flags(name, runs_dir, port):
    command_line_args = run_paths(name, runs_dir)
    command_line_args.update({PORT: port})
    return ' '.join(['--{}={}'.format(flag, value)
                     for flag, value in
                     command_line_args.items()])


def build_command(command, name, port, runs_dir, virtualenv_path):
    command += ' ' + build_flags(name, runs_dir, port)
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


def new(entry,
        name,
        command,
        description,
        virtualenv_path,
        overwrite,
        runs_dir,
        db_filename):
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
    port = choose_port()

    last_commit = next(repo.iter_commits())
    entry.update(dict(datetime=now.isoformat(),
                      command=command,
                      commit=last_commit.hexsha,
                      port=port))
    if description is None:
        entry[DESCRIPTION] = last_commit.message

    command = build_command(command, name, port, runs_dir, virtualenv_path)

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
    with RunDB(path=(os.path.join(runs_dir, db_filename))) as db:
        del db[name]
        for path in run_paths(name, runs_dir).values():
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                try:
                    os.remove(path)
                except FileNotFoundError as e:
                    print(colored(e.strerror + ': ' + path, color='red'))

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


def lookup_from_path(path, name, key,
                     host=None,
                     username=None):
    db = load(path, host, username)
    return lookup(db, name, key)


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
    commit = lookup(db, name, key=COMMIT)
    command = lookup(db, name, key='command')
    description = lookup(db, name, key=DESCRIPTION)
    print('To reproduce:\n',
          code_format('git checkout {}\n'.format(commit)),
          code_format("runs new {} '{}' --description='{}'".format(
              name, command, description)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=None, help='IP address or hostname (without username). Used for accessing '
                                                     'database on remote server.')
    parser.add_argument('--username', default=None, help='Username associated with remote host. Used for accessing '
                                                         'database on remote server.')
    parser.add_argument('--runs-dir', default=DEFAULT_RUNS_DIR, help='Custom path to directory containing runs '
                                                                     'database (default, `runs.yml`). Should not need '
                                                                     'to be specified for local runs but probably '
                                                                     'required for accessing databses remotely.')
    parser.add_argument('--db-filename', default='.runs.yml', help='Name of YAML file storing run database information.')

    subparsers = parser.add_subparsers(dest=DEST)

    virtualenv_path_help = 'Path to virtual environment, if one is being ' \
                           'used. If not `None`, the program will source ' \
                           '`<virtualenv-path>/bin/activate`.'

    new_parser = subparsers.add_parser(NEW, help='Start a new run.')
    new_parser.add_argument(NAME, help='Unique name assigned to new run.')
    new_parser.add_argument(COMMAND, help='Command to run to start tensorflow program.')
    new_parser.add_argument('--virtualenv-path', default='venv', help=virtualenv_path_help)
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
    table_parser.add_argument('--column-width', type=int, default=30, help='Maximum width of table columns. Longer '
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
    reproduce_parser.add_argument('--virtualenv-path', default='venv', help=virtualenv_path_help)
    reproduce_parser.add_argument('--overwrite', action='store_true', help='If this flag is provided, the reproducing '
                                                                           'run will overwrite the reproduced run.')

    visualize_parser = subparsers.add_parser(VISUALIZE,
                                             help='Visualize run with '
                                                  'simplified top-down view')
    visualize_parser.add_argument(NAME, help='Name of run.')

    args = parser.parse_args()
    db_path = os.path.join(args.runs_dir, args.db_filename)
    db = load(db_path, host=args.host, username=args.username)
    if args.runs_dir is DEFAULT_RUNS_DIR and args.host is not None:
        print(colored('Using default path to runs_dir: "{}". '
                      'When accessing remote files, you may want to '
                      'specify the complete path.'.format(DEFAULT_RUNS_DIR),
                      color='red'))
    if args.dest == NEW:
        assert args.host is None, 'SSH into remote before calling runs new.'
        entry = deepcopy(vars(args))
        del entry['name']
        del entry['username']
        del entry['virtualenv_path']
        del entry['runs_dir']
        del entry['db_filename']
        del entry['dest']
        del entry['overwrite']

        new(name=args.name,
            description=args.description,
            virtualenv_path=args.virtualenv_path,
            command=args.command,
            overwrite=args.overwrite,
            entry=entry,
            runs_dir=args.runs_dir,
            db_filename=args.db_filename)

    elif args.dest == DELETE:
        assert args.host is None, 'SSH into remote before calling runs delete.'
        delete(args.pattern, args.db_filename, args.runs_dir)

    elif args.dest == LIST:
        for name in db:
            print(name)

    elif args.dest == TABLE:
        print(get_table_from_path(db_path,
                                  args.column_width,
                                  args.host,
                                  args.username,
                                  args.pattern))

    elif args.dest == LOOKUP:
        print(lookup(db, args.name, args.key))

    elif args.dest == VISUALIZE:
        port = lookup(db, args.name, key=PORT)
        visualizer.run(args.host, port)

    elif args.dest == REPRODUCE:
        reproduce(args.runs_dir, args.db_filename, args.name)

    else:
        raise RuntimeError("'{}' is not a supported dest.".format(args.dest))


if __name__ == '__main__':
    main()
