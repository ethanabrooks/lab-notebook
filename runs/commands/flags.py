import re
from collections import defaultdict
from typing import List

from runs.database import DataBase
from runs.logger import Logger
from runs.transaction.transaction import natural_order
from runs.util import RunPath, natural_order


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'flags', help='Print flags whose cross-product correspond to the queried runs.')
    parser.add_argument('patterns', nargs='+', type=RunPath)
    parser.add_argument(
        '--unless', nargs='*', type=RunPath, help='Exclude these paths from the search.')
    parser.add_argument('--delimiter', default='=', help='Delimiter for flag patterns.')
    return parser


@Logger.wrapper
@DataBase.wrapper
def cli(patterns: List[RunPath], unless: List[RunPath], db: DataBase, delimiter: str,
        *args, **kwargs):
    for string in strings(
            *patterns,
            unless=unless,
            db=db,
            delimiter=delimiter,
    ):
        db.logger.print(string)


def strings(*patterns, unless: List[RunPath], db: DataBase, delimiter: str):
    commands = [e.command for e in db.get(patterns, unless=unless)]
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
