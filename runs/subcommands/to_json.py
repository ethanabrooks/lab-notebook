# stdlib

import json

# first party
from collections import defaultdict
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
        "to-json",
        help="Print json spec that reproduces crossproduct "
        "of args in given patterns.",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        help="String to prepend to all main subcommands, for example, sourcing a "
        "virtualenv",
    )
    parser.add_argument(
        "--exclude", nargs="*", default=set(), help="Keys of args to exclude."
    )
    add_query_args(parser, with_sort=False)
    return parser


@DataBase.open
@DataBase.query
def cli(
    runs: List[RunEntry],
    logger: Logger,
    exclude: List[str],
    prefix: str,
    args: List[str],
    *_,
    **__
):
    if not runs:
        logger.exit("No commands found.")

    exclude = set(exclude)
    commands = [Command.from_run(run).exclude(prefix, *args) for run in runs]
    spec_dict = get_spec_obj(
        commands=commands, exclude=exclude, prefix=prefix, logger=logger
    ).dict()
    spec_dict = {k: v for k, v in spec_dict.items() if v}
    print(json.dumps(spec_dict, sort_keys=True, indent=4))


def get_spec_obj(
    commands: List[Command], exclude: Set[str], prefix: str, logger: Logger
):
    positionals = commands[0].positionals
    args = defaultdict(set)
    flags = set()

    def parse(x):
        try:
            x = float(x)
            if x.is_integer():
                x = int(x)
        except ValueError:
            pass
        return x

    def take_first(it):
        return tuple([parse(x) for x, _ in it])

    def squeeze(x):
        try:
            y, = x
            if not isinstance(y, tuple):
                x = y
        except ValueError:
            pass
        return x

    for command in commands:
        if command.positionals != positionals:
            logger.exit(
                "Command:",
                commands[0],
                "and",
                command,
                "do not have the same positional arguments:",
                sep="\n",
            )

        for (k, _), v in command.optionals:
            args[k].add(squeeze(take_first(v)))

        flags.add(take_first(command.flags))

    flags = list(flags)
    args = {k: squeeze(list(v)) for k, v in args.items()}
    command = "".join([s for t in positionals for s in t])

    return SpecObj(command=command, args=args, flags=flags)
