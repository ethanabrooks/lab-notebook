import itertools
import json
import re
from argparse import ArgumentParser
from collections import defaultdict, namedtuple
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict

from runs.logger import UI
from runs.transaction.transaction import Transaction
from runs.util import PurePath, interpolate_keywords


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'new',
        help='Start a new run.',
        epilog='When there are multiple paths/commands/descriptions, '
               'they get collated. If there is one path but multiple commands, '
               'each path gets appended with a number. Similarly if there is one '
               'description, it gets broadcasted to all paths/commands.')
    assert isinstance(parser, ArgumentParser)

    parser.add_argument(
        '--path',
        dest='paths',
        action='append',
        type=PurePath,
        help='Unique path for each run. '
             'Number of paths and number of commands must be equal.',
        metavar='PATH'
    )
    parser.add_argument(
        '--command',
        dest='commands',
        action='append',
        type=str,
        help='Command to be sent to TMUX for each path.'
             'Number of paths and number of commands must be equal.',
        metavar='COMMAND'
    )
    parser.add_argument(
        '--description',
        dest='descriptions',
        action='append',
        help='Description of this run. Explain what this run was all about or '
             'write whatever your heart desires. If this argument is `commit-message`,'
             'it will simply use the last commit message.')
    parser.add_argument(
        '--prefix',
        type=str,
        help="String to prepend to all main commands, for example, sourcing a virtualenv"
    )
    parser.add_argument(
        '--flag',
        '-f',
        default=[],
        action='append',
        help="directories to create and sync automatically with each run")
    return parser
    # new_parser.add_argument(
    #     '--summary-path',
    #     help='Path where Tensorflow summary of run is to be written.')


Flag = namedtuple('Flag', 'key values')
RunArgs = namedtuple('RunArgs', 'path command description flags')


@Transaction.wrapper
def cli(prefix: str, paths: List[PurePath], commands: List[str], flags: List[str],
        logger: UI, descriptions: List[str], transaction: Transaction,
        *args, **kwargs):
    flags = list(map(parse_flag, flags))
    try:
        # args: RunArgs
        for args in run_args(paths=paths,
                             commands=commands,
                             descriptions=descriptions,
                             flags=flags):
            new_run(**args._asdict(),
                    prefix=prefix,
                    transaction=transaction)
    except AssertionError as e:
        logger.exit(str(e))


def parse_flag(flag: str, delims: str = '=| '):
    """
    :return: a list of [--flag=value] strings
    """
    pattern = f'([^{delims}]*)({delims})(.*)'
    match = re.match(pattern, flag)
    if match:
        key, delim, values = match.groups()
        return Flag(key=key, values=[value for value in values.split('|')])
    else:
        return Flag(key=None, values=flag.split('|'))


def run_args(paths: List[PurePath], commands: List[str],
             descriptions: List[str], flags: List[Flag]):
    n = len(commands)
    assert len(paths) in [1, n], \
        'There must either be 1 or n paths ' \
        'where n is the number of commands.'

    assert len(descriptions) in [0, 1, n], \
        'There must either be 1 or n descriptions ' \
        'where n is the number of commands.'

    iterator = enumerate(itertools.zip_longest(paths,
                                               commands,
                                               descriptions))
    for i, (path, command, description) in iterator:
        if path is None:
            if n == 1:
                path = PurePath(paths[0])
            else:
                path = PurePath(paths[0], str(i))
        if len(descriptions) == 0:
            description = 'Description not given.'
        if len(descriptions) == 1:
            description = descriptions[0]

        flag_sets = list(itertools.product(
            *[[v if flag.key is None else f'{flag.key}={v}'
              for v in flag.values] for flag in flags]))
        for j, flag_set in enumerate(flag_sets):
            new_path = path if len(flag_sets) == 1 else PurePath(path, str(j))
            yield RunArgs(path=new_path,
                          command=command,
                          description=description,
                          flags=flag_set)


def build_command(command: str, path: PurePath, prefix: str, flags: List[str]) -> str:
    if prefix:
        command = f'{prefix} {command}'
    flags = ' '.join(interpolate_keywords(path, f) for f in flags)
    if flags:
        command = f"{command} {flags}"
    return command


def new_run(path: PurePath, prefix: str, command: str, description: str,
            flags: List[str], transaction: Transaction):
    bash = transaction.bash
    full_command = build_command(command, path, prefix, flags)
    if description is None:
        description = ''
    if description == 'commit-message':
        description = bash.cmd('git log -1 --pretty=%B'.split())

    if path in transaction.db:
        transaction.remove(path)

    transaction.add_run(
        path=PurePath(path),
        command=full_command,
        commit=bash.last_commit(),
        datetime=datetime.now().isoformat(),
        description=description)
