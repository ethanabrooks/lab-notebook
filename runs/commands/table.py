# stdlib
from typing import List

# third party
from tabulate import tabulate

# first party
from runs.database import DataBase, add_query_flags
from runs.logger import Logger
from runs.run_entry import RunEntry

DEFAULT_COLUMNS = ['commit', 'datetime', 'description', 'command']


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'table', help='Display contents of run database as a table.')
    add_query_flags(parser, with_sort=True)
    parser.add_argument(
        '--columns',
        nargs='*',
        default=None,
        help='Comma-separated list of columns to display in table. Default is {}'.format(
            ' '.join(DEFAULT_COLUMNS)))
    parser.add_argument(
        '--column-width',
        type=int,
        default=100,
        help='Maximum width of table columns. Longer values will '
        'be truncated and appended with "...".')
    parser.add_argument(
        '--porcelain',
        action='store_true',
        help=
        'This option toggles csv print out (as opposed to formatted print from tabulate)')
    return parser


@DataBase.open
@DataBase.query
def cli(runs: List[RunEntry], logger: Logger, columns: List[str], column_width: int,
        porcelain, *args, **kwargs):
    logger.print(
        string(
            runs=runs, columns=columns, porcelain=porcelain, column_width=column_width))


def string(runs: List[RunEntry],
           porcelain: bool,
           columns: List[str] = None,
           column_width: int = 100):
    if columns is None:
        columns = DEFAULT_COLUMNS
    assert isinstance(column_width, int)

    def get_values(entry, key):
        try:
            value = str(entry.get(key))
            if len(value) > column_width:
                value = value[:column_width] + '...'
            return value
        except AttributeError:
            return '_'

    headers = sorted(columns)
    table = [[e.path] + [get_values(e, key) for key in headers]
             for e in sorted(runs, key=lambda e: e.path)]
    if porcelain:
        return '\n'.join([','.join(map(str, r)) for r in table])
    return tabulate(table, headers=headers)
