import itertools
import re
from collections import defaultdict
from datetime import datetime
from pathlib import PurePath
from typing import List, Tuple

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

    def paths_arg(*arg, nargs, help):
        parser.add_argument(
            *arg,
            nargs=nargs,
            dest='paths',
            action='append',
            type=PurePath,
            help=help,
            metavar='PATH',
        )

    def command_arg(*arg, nargs, help):
        parser.add_argument(
            *arg,
            nargs=nargs,
            dest='commands',
            action='append',
            type=str,
            help=help,
            metavar='COMMAND',
        )

    paths_arg(nargs='?', help='Unique path assigned to new run.')
    paths_arg(
        '--path',
        nargs=None,
        help='Additional paths to create (collated with commands and descriptions).')
    command_arg(nargs='?', help='Command that will be run in tmux.')
    command_arg(
        '--command',
        nargs=None,
        help='Additional commands to run (collated with paths and descriptions).')
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
        help="String to preprend to all main commands, for example, sourcing a virtualenv"
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


@Transaction.wrapper
def cli(prefix: str, paths: List[PurePath], commands: List[str], flags: List[str],
        logger: UI, descriptions: List[str], transaction: Transaction, *args, **kwargs):
    paths = [p for p in paths if p]
    commands = [c for c in commands if c]
    if len(paths) == 0:
        logger.exit('Must provide at least one path.')
    if len(commands) == 0:
        logger.exit('Must provide at least one command.')
    if descriptions is None:
        descriptions = [''] * len(commands)
    elif len(descriptions) == 1:
        descriptions *= len(paths)
        if not len(paths) == len(commands):
            logger.exit('Number of paths must be the same as the number of commands')
    elif not len(paths) == len(commands) == len(descriptions):
        logger.exit(
            f'Got {len(paths)} paths, {len(commands)} commands, and {len(descriptions)} descriptions.'
            f'These numbers should all be the same so that they can be collated.')
    runs = defaultdict(list)
    for path, command, description in zip(paths, commands, descriptions):
        for parsed_flags in generate_runs(flags):
            runs[path].append((command, parsed_flags, description))

    for path in runs:
        for i, (command, flags, description) in enumerate(runs[path]):
            new_path = path
            if len(runs[path]) > 1:
                new_path = PurePath(path, str(i))
            new(path=new_path,
                prefix=prefix,
                command=command,
                description=description,
                flags=flags,
                transaction=transaction)


def parse_flag(flag, delims='=| '):
    pattern = f'([^{delims}]*)({delims})(.*)'
    match = re.match(pattern, flag)
    if match:
        key, delim, values = match.groups()
        return [f'{key}{delim}{value}' for value in values.split('|')]
    else:
        return flag.split('|')


def generate_runs(flags: List[str]) -> Tuple[PurePath, List[str]]:
    flags = [parse_flag(flag) for flag in flags]
    return itertools.product(*flags)


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
        path=PurePath(path),
        command=full_command,
        commit=bash.last_commit(),
        datetime=datetime.now().isoformat(),
        description=description)
