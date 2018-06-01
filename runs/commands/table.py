from runs.database import DataBase
from runs.run_entry import RunEntry
from runs.logger import Logger
from runs.util import PATTERN, TABLE, nonempty_string
from tabulate import tabulate

help = 'Only display paths matching this pattern.'


def add_subparser(subparsers):
    table_parser = subparsers.add_parser(
        TABLE, help='Display contents of run database as a table.')
    table_parser.add_argument(
        PATTERN, nargs='?', default=None, help=help, type=nonempty_string)
    table_parser.add_argument(
        '--hidden-columns',
        default=None,
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
def cli(pattern, db, hidden_columns, column_width, *args, **kwargs):
    db.logger.print(string(db, pattern, hidden_columns, column_width))


def string(db, pattern=None, hidden_columns=None, column_width=100):
    if hidden_columns is None:
        hidden_columns = ['full_command', 'path']
    else:
        hidden_columns = hidden_columns.split(',')
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
    entries = db[pattern] if pattern else db.all()
    db = [[e.path] + [get_values(e, key) for key in headers]
          for e in sorted(entries, key=lambda e: e.path)]
    return tabulate(db, headers=headers)
