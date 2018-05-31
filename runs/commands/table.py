from tabulate import tabulate

from runs.database import Table, RunEntry
from runs.logger import Logger
from runs.util import PATTERN, TABLE, nonempty_string


def add_table_parser(pattern_help, subparsers):
    table_parser = subparsers.add_parser(
        TABLE, help='Display contents of run database as a table.')
    table_parser.add_argument(
        PATTERN,
        nargs='?',
        default=None,
        help=pattern_help,
        type=nonempty_string)
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
@Table.wrapper
def cli(pattern, table, hidden_columns, column_width, *args, **kwargs):
    table.logger.print(string(table, pattern, hidden_columns, column_width))


def string(table, pattern, hidden_columns=None, column_width=100):
    if pattern is None:
        pattern = '%'
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
    table = [[e.path] + [get_values(e, key) for key in headers]
             for e in sorted(table[pattern], key=lambda e: e.path)]
    return tabulate(table, headers=headers)
