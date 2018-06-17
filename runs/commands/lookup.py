from typing import Dict, List

from runs.commands import table
from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import highlight, RunPath


def add_subparser(subparsers):
    lookup_parser = subparsers.add_parser(
        'lookup', help='Lookup specific value associated with database entry')
    lookup_parser.add_argument(
        'key',
        choices=RunEntry.fields() + ('all', ),
        help='Key that value is associated with.')
    lookup_parser.add_argument(
        'patterns',
        help='Pattern of runs for which to retrieve key.',
        type=RunPath,
        nargs='*')
    lookup_parser.add_argument('--porcelain', action='store_true')
    return lookup_parser


@Logger.wrapper
@DataBase.wrapper
def cli(patterns: List[RunPath], key: str, db: DataBase, porcelain: bool, *args,
        **kwargs):
    db.logger.print(string(*patterns, db=db, key=key, porcelain=porcelain))


def string(*patterns, db: DataBase, key: str, porcelain: bool = True) -> str:
    return '\n'.join(strings(*patterns, db=db, key=key, porcelain=porcelain))


def strings(*patterns, db: DataBase, key: str, porcelain: bool) -> List[str]:
    if key == 'all':
        if porcelain:
            for entry in db[patterns, ]:
                yield str(entry)
        else:
            yield table.string(*patterns, db=db)
    else:
        attr_dict = get_dict(*patterns, db=db, key=key)
        if porcelain:
            for value in attr_dict.values():
                yield str(value)
        else:
            for path, attr in attr_dict.items():
                yield highlight(path, ": ", sep='') + str(attr)


def get_dict(*pattern, db: DataBase, key: str) -> Dict[RunPath, str]:
    return {entry.path: entry.get(key) for entry in (db[pattern])}
