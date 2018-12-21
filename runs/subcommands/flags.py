# stdlib
from collections import defaultdict
import re
from typing import List

# first party
from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.utils.arguments import add_query_args
from runs.utils.util import natural_order


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'args', help='Print args whose cross-product correspond to the queried runs.')
    add_query_args(parser, with_sort=False)
    parser.add_argument('--delimiter', default='=', help='Delimiter for arg patterns.')
    return parser


@DataBase.open
@DataBase.query
def cli(logger: Logger, runs: List[RunEntry], delimiter: str, *_, **__):
    for string in strings(
            runs=runs,
            delimiter=delimiter,
    ):
        logger.print(string)


def strings(runs: List[RunEntry], delimiter: str):
    commands = [e.command for e in runs]
    arg_dict = parse_args(commands, delimiter=delimiter)
    return [
        f'{f}{delimiter}{"|".join(sorted(v, key=natural_order))}'
        for f, v in arg_dict.items()
    ]


def parse_args(commands: List[str], delimiter: str):
    args = defaultdict(set)
    for command in commands:
        for word in command.split():
            if delimiter in command:
                pattern = f'([^{delimiter}]*)({delimiter})(.*)'
                match = re.match(pattern, word)
                if match:
                    key, delim, value = match.groups()
                    args[key].add(value)
    return args
