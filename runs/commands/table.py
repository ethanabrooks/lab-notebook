from pathlib import PurePath
from typing import List

from tabulate import tabulate

from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import comma_sep_list

help = 'Only display paths matching this pattern.'


def add_subparser(subparsers):
    table_parser = subparsers.add_parser(
        'table', help='Display contents of run database as a table.')
    table_parser.add_argument('pattern', nargs='*', help=help, type=PurePath)
    table_parser.add_argument(
        '--hidden-columns',
        type=comma_sep_list,
        default='full_command,path',
        help='Comma-separated list of columns to not display in table.')
    table_parser.add_argument(
        '--column-width',
        type=int,
        default=100,
        help='Maximum width of table columns. Longer values will '
        'be truncated and appended with "...".')
    return table_parser


@Logger.wrapper
@DataBase.wrapper
def cli(pattern: List[PurePath], db: DataBase, hidden_columns: List[str],
        column_width: int, *args, **kwargs):
    db.logger.print(
        string(*pattern, db=db, hidden_columns=hidden_columns, column_width=column_width))


def string(*patterns, db: DataBase, hidden_columns=None, column_width: int = 100):
    if hidden_columns is None:
        hidden_columns = []
    assert isinstance(column_width, int)

    def get_values(entry, key):
        try:
            value = str(entry.get(key))
            if len(value) > column_width:
                value = value[:column_width] + '...'
            return value
        except AttributeError:
            return '_'

    headers = sorted(set(RunEntry.fields()) - set(hidden_columns))
    entries = db.descendants(*patterns) if patterns else db.all()
    db = [[e.path] + [get_values(e, key) for key in headers]
          for e in sorted(entries, key=lambda e: e.path)]
    return tabulate(db, headers=headers)
