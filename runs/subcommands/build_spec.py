# stdlib

# first party
from collections import defaultdict
from pprint import pprint
import re
from typing import List, Set

from runs.arguments import add_query_args
from runs.command import Command
from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.subcommands.new_from_spec import SpecObj


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'build-spec',
        help='Print json spec that reproduces crossproduct '
        'of args in given patterns.')
    parser.add_argument(
        '--exclude', nargs='*', default=set(), help='Keys of args to exclude.')
    add_query_args(parser, with_sort=False)
    return parser


@DataBase.open
@DataBase.query
def cli(runs: List[RunEntry], logger: Logger, exclude: List[str], *_, **__):
    exclude = set(exclude)
    commands = [Command.from_run(run) for run in runs]
    for command in commands:
        for group in command.arg_groups[1:]:
            if isinstance(group, list):
                logger.exit(f"Command {command} contains multiple positional argument "
                            f"groups. Currently reproduce-to-spec only supports one "
                            f"positional argument group")
    stems = {' '.join(command.stem) for command in commands}
    if not len(stems) == 1:
        logger.exit(
            "Commands do not start with the same positional arguments:",
            *commands,
            sep='\n')
    pprint(get_spec_obj(commands, exclude).dict())


def get_spec_obj(commands: List[Command], exclude: Set[str]):
    stem = ' '.join(commands[0].stem)

    def group(pairs):
        _dict = defaultdict(list)
        for k, v in pairs:
            _dict[k].append(v)
        return _dict

    def get_args(command: Command):
        try:
            nonpositionals = command.arg_groups[1]
            for arg in nonpositionals:
                match = re.match('(-{1,2}[^=]*)=(.*)', arg).groups()
                if match is not None:
                    key, value = match
                    key = key.lstrip('--')
                else:
                    value, = re.match('(-{1,2}.*)', arg).groups()
                    value = value.lstrip('--')
                    key = None
                if key not in exclude:
                    yield key, value
        except IndexError:
            yield None, None

    def args():
        for k, values in  group(group(get_args(command)) for command in commands).items():
            for v in values:
                if isinstance(v, list):
                    yield from ((k, value) for value in v)
                else:
                    yield (k, v)

    args = group(group(get_args(command)) for command in commands)
    args = {k: v.pop() if len(v) == 1 and len(v[0]) == 1 else list(v) for k,
                                                                      v in args.items()}
    return SpecObj(command=stem, args=args)
