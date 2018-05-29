from runs.database import Table
from runs.logger import Logger
from runs.util import LIST, PATTERN, nonempty_string


def add_list_parser(pattern_help, subparsers):
    list_parser = subparsers.add_parser(
        LIST, help='List all names in run database.')
    list_parser.add_argument(
        PATTERN, nargs='?', help=pattern_help, type=nonempty_string)
    list_parser.add_argument(
        '--show-attrs',
        action='store_true',
        help='Print run attributes in addition to names.')
    list_parser.add_argument(
        '--porcelain',
        action='store_true',
        help='Print list of path names without tree '
             'formatting.')
    return list_parser


@Logger.wrapper
@Table.wrapper
def cli(pattern, table, *args, **kwargs):
    for string in strings(pattern, table):
        print(string)


def strings(pattern, table):
    if pattern is None:
        pattern = '%'
    return [e.path for e in table[pattern]]
