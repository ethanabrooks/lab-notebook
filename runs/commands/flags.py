# stdlib
from collections import defaultdict
import re
from typing import List

# first party
from runs.database import DataBase, add_query_flags
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import natural_order


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'flags', help='Print flags whose cross-product correspond to the queried runs.')
    add_query_flags(parser, with_sort=False)
    parser.add_argument('--delimiter', default='=', help='Delimiter for flag patterns.')
    return parser


@DataBase.open
@DataBase.query
def cli(logger: Logger, runs: List[RunEntry], delimiter: str, *args, **kwargs):
    for string in strings(
            runs=runs,
            delimiter=delimiter,
    ):
        logger.print(string)


def strings(runs: List[RunEntry], delimiter: str):
    commands = [e.command for e in runs]
    flag_dict = parse_flags(commands, delimiter=delimiter)
    return [
        f'{f}{delimiter}{"|".join(sorted(v, key=natural_order))}'
        for f, v in flag_dict.items()
    ]


def parse_flags(commands: List[str], delimiter: str):
    flags = defaultdict(set)
    for command in commands:
        for word in command.split():
            if delimiter in command:
                pattern = f'([^{delimiter}]*)({delimiter})(.*)'
                match = re.match(pattern, word)
                if match:
                    key, delim, value = match.groups()
                    flags[key].add(value)
    return flags
