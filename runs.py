#!/usr/bin/env python
from contextlib import contextmanager
from getpass import getpass

from paramiko import SSHException
from paramiko.client import SSHClient, AutoAddPolicy
import argparse
import glob
import os
import re
import shutil
import socket
import warnings
from copy import deepcopy
from datetime import datetime

import libtmux
import yaml
from git import Repo
from tabulate import tabulate
from termcolor import colored

import visualizer

DEST = 'dest'
RUNS = '.runs'
NAME = 'name'
COMMAND = 'command'
DATETIME = 'datetime'
TB_DIR = 'tb-dir'
GOAL_LOG_FILE = 'goal-log-file'
SAVE_PATH = 'save-path'
RECORDS = 'records'

NEW = 'new'
SAVE = 'save'
DELETE = 'delete'
LOOKUP = 'lookup'
LIST = 'list'
TABLE = 'table'
VISUALIZE = 'visualize'

BUFFSIZE = 1024


def code_format(*args):
    string = ' '.join(map(str, args))
    return colored(string, color='white', attrs=['dark'])


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
        client.connect(host, username=username, look_for_keys=False)
    except SSHException:
        client.connect(host, username=username, password=getpass("Enter password:"), look_for_keys=False)
    if not client:
        raise RuntimeError("Connection not opened.")

    with client.open_sftp().open(remote_filename) as f:
        yield f


def run_paths(run_name, runs_dir):
    return {'tb-dir': os.path.join(runs_dir, 'tensorboard', run_name + '/'),
            'save-path': os.path.join(runs_dir, 'checkpoints', run_name + '.ckpt'),
            'goal-log-file': os.path.join(runs_dir, 'goal-logs', run_name + '.log')}


def make_dirs(run_name, runs_dir):
    for path in run_paths(run_name, runs_dir).values():
        dirname = os.path.dirname(path)
        os.makedirs(dirname, exist_ok=True)


def commit(description, no_commit):
    if description is None:
        description = input("Provide description of run:")
    repo = Repo()
    if repo.is_dirty() and not no_commit:
        repo.index.commit(description)


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
    command_line_args.update({'port': port})
    return ' '.join(['--{}={}'.format(flag, value)
                     for flag, value in
                     command_line_args.items()])


def source_virtualenv_command(virtualenv_path):
    return 'source ' + virtualenv_path + '/bin/activate;'


def run_tmux(name, window_name, command):
    server = libtmux.Server()
    server.new_session(name, kill_session=True)
    session = server.find_where(
        dict(session_name=name))  # type: libtmux.Session
    pane = session.new_window(window_name).attached_pane
    pane.send_keys(command)


def new(name, description, virtualenv_path, command, no_commit,
        overwrite, entry, runs_dir, db_filename):
    assert '.' not in name

    # deal with collisions
    db_path = os.path.join(runs_dir, db_filename)
    if name in load(db_path):
        if overwrite:
            delete_run(name, db_filename, runs_dir)
        else:
            rename(name, db_filename, runs_dir)

    make_dirs(name, runs_dir)
    commit(description, no_commit)
    port = choose_port()
    command += ' ' + build_flags(name, runs_dir, port)
    if virtualenv_path:
        command = source_virtualenv_command(virtualenv_path) + ' ' + command

    run_tmux(name, description, command)
    print('Command sent to session:')
    print(code_format(command))

    entry[COMMAND] = command
    entry[DATETIME] = datetime.now().isoformat()
    with RunDB(path=db_path) as db:
        db[name] = entry

    print('List active:')
    print(code_format('tmux list-session'))
    print('Attach:')
    print(code_format('tmux attach -t', name))


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
                    warnings.warn(colored(e.strerror, color='red', attrs=['dark']))

        server = libtmux.Server()
        session = server.find_where(
            dict(session_name=name))  # type: libtmux.Session
        if session:
            session.kill_session()


def delete(pattern, db_filename, runs_dir):
    db_path = os.path.join(runs_dir, db_filename)
    pattern = '^' + pattern + '$'
    with RunDB(path=db_path) as db:
        runs_to_delete = [name for name in db.keys()
                          if re.match(pattern, name) is not None]
    if runs_to_delete:
        for run_name in runs_to_delete:
            delete_run(run_name, db_filename, runs_dir)
            print('Deleted', run_name)
    else:
        print('No runs match pattern. Recorded runs:')
        for name in load(db_path):
            print(name)


def rename(name, db_filename, runs_dir):
    new_name = name + '@' + datetime.now().isoformat()

    with RunDB(path=(os.path.join(runs_dir, db_filename))) as db:
        db[new_name] = db[name]
        del db[name]

    for pattern in run_paths(name, runs_dir).values():
        for path in glob.glob(pattern + '*'):  # glob is necessary for .ckpt files
            os.rename(path, path.replace(name, new_name))


def lookup_from_path(path, name, key,
                     host=None,
                     username=None):
    db = load(path, host, username)
    return lookup(db, name, key)


def lookup(db, name, key):
    if name not in db.keys():
        raise KeyError(
            "`{}` is not a documented run. Documented runs are {}.".format(
                name, db.keys()))
    entry = db[name]
    if key not in entry:
        raise KeyError(
            "`{}` not a valid key. Valid keys are {}.".format(
                key, entry.keys()))
    return entry[key]


def get_table_from_path(db_path, maxlen, host, username):
    db = load(db_path, host, username)
    get_table(db, maxlen)


def get_table(db, maxlen):
    def get_values(entry, key):
        try:
            value = str(entry[key])
            if len(value) > maxlen:
                value = value[:maxlen] + '...'
            return value
        except KeyError:
            return '_'

    headers = sorted(set(key for _, entry in db.items() for key in entry))
    table = [[name] + [get_values(entry, key) for key in headers]
             for name, entry in db.items()]
    headers = [NAME] + list(headers)
    return tabulate(table, headers=headers)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=None)
    parser.add_argument('--username', default=None)
    parser.add_argument('--runs-dir', default='.runs')
    parser.add_argument('--db-filename', default='.runs.yml')

    subparsers = parser.add_subparsers(dest=DEST)

    new_parser = subparsers.add_parser(NEW, help='save run info')
    new_parser.add_argument(NAME)
    new_parser.add_argument(COMMAND)
    new_parser.add_argument('--virtualenv-path', default='venv')
    new_parser.add_argument('--no-commit', action='store_true')
    new_parser.add_argument('--overwrite', action='store_true')
    new_parser.add_argument('--description')

    delete_parser = subparsers.add_parser(DELETE, help='delete run info')
    delete_parser.add_argument('pattern')

    list_parser = subparsers.add_parser(LIST, help='list run names')

    table_parser = subparsers.add_parser(TABLE, help='table of run info')
    table_parser.add_argument('--maxlen', type=int, default=30)

    lookup_parser = subparsers.add_parser(LOOKUP, help='lookup run info')
    lookup_parser.add_argument(NAME)
    lookup_parser.add_argument('key')

    visualize_parser = subparsers.add_parser(VISUALIZE,
                                             help='visualize run with '
                                                  'simplified top-down view')
    visualize_parser.add_argument(NAME)
    visualize_parser.add_argument('--db-path',
                                  default='$HOME/zero_shot/.runs/.runs.yml',
                                  help='Needs to be in yaml format.')

    args = parser.parse_args()
    db_path = os.path.join(args.runs_dir, args.db_filename)
    db = load(db_path, host=args.host, username=args.username)
    if args.dest == NEW:
        assert args.host is None, 'SSH into remote before calling run.py new.'
        entry = deepcopy(vars(args))
        del entry['name']
        del entry['virtualenv_path']
        del entry['no_commit']
        del entry['runs_dir']
        del entry['db_filename']
        del entry['dest']
        del entry['host']
        del entry['overwrite']

        new(name=args.name,
            description=args.description,
            virtualenv_path=args.virtualenv_path,
            command=args.command,
            no_commit=args.no_commit,
            overwrite=args.overwrite,
            entry=entry,
            runs_dir=args.runs_dir,
            db_filename=args.db_filename)

    elif args.dest == DELETE:
        delete(args.pattern, args.db_filename, args.runs_dir)

    elif args.dest == LIST:
        for name in db:
            print(name)

    elif args.dest == TABLE:
        print(get_table(db, args.maxlen))

    elif args.dest == LOOKUP:
        print(lookup(db, args.name, args.key))

    elif args.dest == VISUALIZE:
        port = lookup(db, args.name, key='port')
        visualizer.run(args.host, port)
    else:
        raise RuntimeError("'{}' is not a supported dest.".format(args.dest))

if __name__ == '__main__':
    main()
