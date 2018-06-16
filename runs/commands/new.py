import itertools
from datetime import datetime
from pathlib import PurePath
from typing import List

from runs.transaction import Transaction
from runs.util import flag_list, nonempty_string_type


def add_subparser(subparsers):
    parser = subparsers.add_parser('new', help='Start a new run.')
    parser.add_argument(
        'path',
        help='Unique path assigned to new run. "\\"-delimited.',
        type=nonempty_string_type)
    parser.add_argument('command', help='Command that will be run in tmux.', type=str)
    parser.add_argument(
        '--description',
        help='Description of this run. Explain what this run was all about or '
        'just write whatever your heart desires. If this argument is `commit-message`,'
        'it will simply use the last commit message.')
    parser.add_argument(
        '--prefix',
        type=str,
        help="String to preprend to all main commands, for example, sourcing a virtualenv"
    )
    parser.add_argument(
        '--flags',
        type=flag_list,
        help="directories to create and sync automatically with each run")
    return parser
    # new_parser.add_argument(
    #     '--summary-path',
    #     help='Path where Tensorflow summary of run is to be written.')


@Transaction.wrapper
def cli(path: PurePath, prefix: str, command: str, description: str,
        flags: List[List[str]], transaction: Transaction, *args, **kwargs):
    runs = list(generate_runs(path, flags))

    for path, flags in runs:
        new(path=path,
            prefix=prefix,
            command=command,
            description=description,
            flags=flags,
            transaction=transaction)


def generate_runs(path: PurePath, flags: List[List[str]]):
    flag_combinations = list(itertools.product(*flags))
    for i, flags in enumerate(flag_combinations):
        new_path = path
        if len(flag_combinations) > 1:
            new_path += str(i)
        yield new_path, flags


def build_command(command: str, path: PurePath, prefix: str, flags: List[str]) -> str:
    if prefix:
        command = f'{prefix} {command}'
    flags = ' '.join(interpolate_keywords(path, f) for f in flags)
    if flags:
        command = f"{command} {flags}"
    return command


def new(path: PurePath, prefix: str, command: str, description: str, flags: List[str],
        transaction: Transaction):
    bash = transaction.bash
    full_command = build_command(command, path, prefix, flags)
    if description is None:
        description = ''
    if description == 'commit-message':
        description = bash.cmd('git log -1 --pretty=%B'.split())

    if path in transaction.db:
        transaction.remove(path)

    transaction.add_run(
        path=path,
        full_command=full_command,
        commit=bash.last_commit(),
        datetime=datetime.now().isoformat(),
        description=description,
        input_command=command)


def interpolate_keywords(path, string):
    keywords = dict(path=path, name=PurePath(path).stem)
    for word, replacement in keywords.items():
        string = string.replace(f'<{word}>', str(replacement))
    return string
