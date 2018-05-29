from runs.database import RunEntry, Table
from runs.logger import Logger
from runs.util import nonempty_string


def add_lookup_parser(subparsers):
    lookup_parser = subparsers.add_parser(
        'lookup', help='Lookup specific value associated with database entry')
    lookup_parser.add_argument(
        'path',
        help='Pattern of runs for which to retrieve key.',
        type=nonempty_string)
    lookup_parser.add_argument(
        'key',
        default=None,
        nargs='?',
        help='Key that value is associated with.')
    return lookup_parser


@Logger.wrapper
@Table.wrapper
def cli(path, key, table, *args, **kwargs):
    print(string(table, path, key, table.logger))


def string(table, path, key, logger):
    entry = table.entry(path)
    if key is None:
        return entry
    elif hasattr(entry, key):
        return getattr(entry, key)
    else:
        logger.exit(
            f"{key} is not a valid key. Valid keys are:",
            RunEntry.fields(),
            sep='\n')
