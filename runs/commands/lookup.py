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
        logger.print(string(table=table,
                            pattern=pattern,
                            key=key,
                            porcelain=porcelain))
    except RunEntry.KeyError:
        logger.exit(
            f"{key} is not a valid key. Valid keys are:",
            RunEntry.fields(),
            sep='\n')


def string(table, pattern, key, porcelain=True):
    return '\n'.join(strings(table, pattern, key, porcelain))


def strings(table, pattern, key, porcelain):
    if key:
        attr_dict = get_dict(table, pattern, key)
        if porcelain:
            for value in attr_dict.values():
                yield str(value)
        else:
            for path, attr in attr_dict.items():
                yield f'{path}.{key} = {attr}'
    else:
        if porcelain:
            for entry in table[pattern]:
                yield str(entry)
        else:
            yield runs.commands.table.string(table, pattern)


def get_dict(table, path, key):
    return {entry.path: entry.get(key) for entry in (table[path])}
