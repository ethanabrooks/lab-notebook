from runs.database import Table
from runs.logger import Logger
from runs.util import CHDESCRIPTION, PATH, nonempty_string, string_from_vim


def add_chdesc_parser(subparsers):
    chdesc_parser = subparsers.add_parser(
        CHDESCRIPTION, help='Edit description of run.')
    chdesc_parser.add_argument(
        PATH,
        help='Name of run whose description you want to edit.',
        type=nonempty_string)
    chdesc_parser.add_argument(
        'description',
        nargs='?',
        default=None,
        help='New description. If None, script will prompt for '
        'a description in Vim')
    return chdesc_parser


@Logger.wrapper
@Table.wrapper
def cli(path, description, table, *args, **kwargs):
    entry = table.entry(path)
    if description is None:
        description = string_from_vim('Edit description', entry.description)
    table.update(path, description=description)
