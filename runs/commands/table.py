from typing import List, Optional

from tabulate import tabulate

from runs.database import DataBase
from runs.logger import Logger
from runs.util import RunPath

DEFAULT_COLUMNS = ['commit', 'datetime', 'description', 'command']


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'table', help='Display contents of run database as a table.')
    parser.add_argument(
        'pattern',
        nargs='*',
        help='Only display paths matching this pattern.',
        type=RunPath)
    parser.add_argument(
        '--unless', nargs='*', type=RunPath, help='Exclude these paths from the output.')
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
        '--porcelain', action='store_true',
        help='This option toggles csv print out (as opposed to formatted print from tabulate)')
    return parser


@Logger.wrapper
@DataBase.wrapper
def cli(pattern: List[RunPath], unless: List[RunPath], db: DataBase, columns: List[str],
        column_width: int, porcelain, *args, **kwargs):
    db.logger.print(
        string(
            *pattern, unless=unless, db=db, columns=columns, column_width=column_width))


def string(*patterns,
           unless: List[RunPath] = None,
           db: DataBase,
           columns: List[str] = None,
           porcelain: bool,
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
    entries = db.descendants(*patterns, unless=unless) if patterns else db.all()
    table = [[e.path] + [get_values(e, key) for key in headers]
             for e in sorted(entries, key=lambda e: e.path)]
    if porcelain:
        return '\n'.join([','.join(r) for r in table])
    return tabulate(table, headers=headers)
