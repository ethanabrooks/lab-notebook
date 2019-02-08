# stdlib

# first party
from collections import defaultdict
import json
from typing import List, Set

from runs.arguments import add_query_args
from runs.command import Command
from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.subcommands.from_json import SpecObj
from runs.util import get_args


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'to-json',
        help='Print json spec that reproduces crossproduct '
        'of args in given patterns.')
    parser.add_argument(
        '--exclude', nargs='*', default=set(), help='Keys of args to exclude.')
    add_query_args(parser, with_sort=False)
    return parser


@DataBase.open
@DataBase.query
def cli(runs: List[RunEntry], logger: Logger, exclude: List[str], prefix: str,
        args: List[str], *_, **__):
    if not runs:
        logger.exit("No commands found.")

    exclude = set(exclude)
    commands = [Command.from_run(run) for run in runs]
    for command in commands:
        for group in command.arg_groups[1:]:
            if isinstance(group, list):
                logger.exit(f'Command "{command}" contains multiple positional argument '
                            f"groups. Currently reproduce-to-spec only supports one "
                            f"positional argument group")
    stems = {' '.join(command.stem) for command in commands}
    if len(stems) > 1:
        logger.exit(
            "Commands do not start with the same positional arguments:",
            *commands,
            sep='\n')
    spec_dict = get_spec_obj(commands=commands, exclude=exclude, prefix=prefix).dict()
    spec_dict = {k: v for k, v in spec_dict.items() if v}
    print(json.dumps(spec_dict, sort_keys=True, indent=4))


def get_spec_obj(commands: List[Command], exclude: Set[str], prefix: str):
    stem = ' '.join(commands[0].stem).lstrip(prefix)

    def group(pairs):
        d = defaultdict(list)
        for k, v in pairs:
            d[k].append(v)
        return d

    def squeeze(x):
        if len(x) == 1 and not isinstance(x[0], list):
            return x[0]
        return x

    def remove_duplicates(values):
        values = set(map(tuple, values))
        return list(map(list, values))

    # get {key: [values]} dict for command (from '{--key}={value}')
    command_args = [group(get_args(c, exclude)) for c in commands]

    # add field for flags if not present
    for args in command_args:
        if None not in args:
            args[None] = []

    grouped_args = group((pair for args in command_args for pair in args.items()))
    flags = remove_duplicates(grouped_args.pop(None, []))

    def preprocess(values):
        values = remove_duplicates(values)
        values = list(map(squeeze, values))
        return squeeze(values)

    args = {k: preprocess(v) for k, v in grouped_args.items()}

    return SpecObj(command=stem, args=args, flags=flags or None)
