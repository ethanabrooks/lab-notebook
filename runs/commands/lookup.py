import runs
from runs.database import RunEntry, Table
from runs.logger import Logger
from runs.util import nonempty_string


def add_subparser(subparsers):
    lookup_parser = subparsers.add_parser(
        'lookup', help='Lookup specific value associated with database entry')
    lookup_parser.add_argument(
        'pattern',
        help='Pattern of runs for which to retrieve key.',
        type=nonempty_string)
    lookup_parser.add_argument(
        'key',
        default=None,
        nargs='?',
        help='Key that value is associated with.')
    lookup_parser.add_argument(
        '--porcelain',
        action='store_true')
    return lookup_parser


@Logger.wrapper
@Table.wrapper
def cli(pattern, key, table, porcelain, *args, **kwargs):
    logger = table.logger
    try:
        for string in strings(table, pattern, key, porcelain):
            logger.print(string)
    except RunEntry.KeyError:
        logger.exit(
            f"{key} is not a valid key. Valid keys are:",
            RunEntry.fields(),
            sep='\n')


def strings(table, pattern, key, porcelain=True):
    if key:
        attr_dict = get_dict(table, pattern, key)
        if porcelain:
            return [attr for attr in attr_dict.values()]
        else:
            return [f'{path}.{key} = {attr}'
                    for path, attr in attr_dict.items()]
    else:
        if porcelain:
            return [attr for attr in table[pattern]]
        else:
            return [runs.commands.table.string(table, pattern)]


def get_dict(table, path, key):
    return {entry.path: entry.get(key) for entry in (table[path])}
