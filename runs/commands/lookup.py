import runs
from runs.database import RunEntry, DataBase
from runs.logger import Logger
from runs.util import highlight
from runs.util import nonempty_string


def add_subparser(subparsers):
    lookup_parser = subparsers.add_parser(
        'lookup', help='Lookup specific value associated with database entry')
    lookup_parser.add_argument(
        'pattern',
        help='Pattern of runs for which to retrieve key.',
        type=nonempty_string)
    lookup_parser.add_argument(
        'key', default=None, nargs='?', help='Key that value is associated with.')
    lookup_parser.add_argument('--porcelain', action='store_true')
    return lookup_parser


@Logger.wrapper
@DataBase.wrapper
def cli(pattern, key, db, porcelain, *args, **kwargs):
    logger = db.logger
    try:
        logger.print(string(db=db, pattern=pattern, key=key, porcelain=porcelain))
    except RunEntry.KeyError:
        logger.exit(
            f"{key} is not a valid key. Valid keys are:", RunEntry.fields(), sep='\n')


def string(db, pattern, key, porcelain=True):
    return '\n'.join(strings(db, pattern, key, porcelain))


def strings(db, pattern, key, porcelain):
    if key:
        attr_dict = get_dict(db, pattern, key)
        if porcelain:
            for value in attr_dict.values():
                yield str(value)
        else:
            for path, attr in attr_dict.items():
                yield highlight(path + ": ") + str(attr)
    else:
        if porcelain:
            for entry in db[pattern]:
                yield str(entry)
        else:
            yield runs.commands.table.string(db, pattern)


def get_dict(db, path, key):
    return {entry.path: entry.get(key) for entry in (db[path])}
