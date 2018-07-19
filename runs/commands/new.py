import itertools
import re
from datetime import datetime
from pathlib import PurePath
from typing import List, Tuple

from collections import defaultdict

from runs.transaction.transaction import Transaction
from runs.util import RunPath, interpolate_keywords


def add_subparser(subparsers):
    parser = subparsers.add_parser('new', help='Start a new run.')

    def paths_arg(*arg, nargs):
        parser.add_argument(
            *arg,
            nargs=nargs,
            dest='paths',
            action='append',
            type=RunPath,
            help='Unique path assigned to new run.',
        )

    def command_arg(*arg, nargs):
        parser.add_argument(
            *arg,
            nargs=nargs,
            dest='commands',
            action='append',
            type=str,
            help='Command that will be run in tmux.',
        )

    paths_arg(nargs='?')
    paths_arg('--path', nargs=None)
    command_arg(nargs='?')
    command_arg('--command', nargs=None)
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
def cli(prefix: str, paths: List[RunPath], commands: List[str], flags: List[str],
        descriptions: List[str], transaction: Transaction, *args, **kwargs):
    paths = [p for p in paths if p]
    commands = [c for c in commands if c]
    if len(descriptions) == 1:
        descriptions *= len(paths)
        if not len(paths) == len(commands):
            transaction.db.logger.exit(
                'Number of paths must be the same as the number of commands')
    elif not len(paths) == len(commands) == len(descriptions):
        import ipdb; ipdb.set_trace()
        transaction.db.logger.exit(
            f'Got {len(paths)} paths, {len(commands)} commands, and {len(descriptions)} descriptions.'
            f'These numbers should all be the same so that they can be collated.')
    runs = defaultdict(list)
    for path, command, description in zip(paths, commands, descriptions):
        for parsed_flags in generate_runs(flags):
            runs[path].append((command, parsed_flags, description))

    for path in runs:
        for i, (command, flags, description) in enumerate(runs[path]):
            if len(runs[path]) > 1:
                path = RunPath(path, str(i))
            new(path=path,
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


def generate_runs(flags: List[str]) -> Tuple[RunPath, List[str]]:
    flags = [parse_flag(flag) for flag in flags]
    return itertools.product(*flags)


def build_command(command: str, path: RunPath, prefix: str, flags: List[str]) -> str:
    if prefix:
        command = f'{prefix} {command}'
    flags = ' '.join(interpolate_keywords(path, f) for f in flags)
    if flags:
        command = f"{command} {flags}"
    return command


def new(path: RunPath, prefix: str, command: str, description: str, flags: List[str],
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
