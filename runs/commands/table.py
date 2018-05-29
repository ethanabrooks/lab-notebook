from runs.util import PATTERN, TABLE, nonempty_string


def add_table_parser(pattern_help, subparsers):
    table_parser = subparsers.add_parser(
        TABLE, help='Display contents of run database as a table.')
    table_parser.add_argument(
        PATTERN,
        nargs='?',
        default='*',
        help=pattern_help,
        type=nonempty_string)
    table_parser.add_argument(
        '--hidden-columns',
        help='Comma-separated list of columns to not display in table.')
    table_parser.add_argument(
        '--column-width',
        type=int,
        default=100,
        help='Maximum width of table columns. Longer values will '
        'be truncated and appended with "...".')
    return table_parser
