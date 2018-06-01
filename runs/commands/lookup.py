from pathlib import PurePath
from typing import Dict, List

from runs.commands import table
from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import highlight


def add_subparser(subparsers):
    lookup_parser = subparsers.add_parser(
        'lookup', help='Lookup specific value associated with database entry')
    lookup_parser.add_argument(
        'pattern', help='Pattern of runs for which to retrieve key.', type=PurePath)
    lookup_parser.add_argument(
        'key',
        choices=RunEntry.fields(),
        default=None,
        nargs='?',
        help='Key that value is associated with.')
    lookup_parser.add_argument('--porcelain', action='store_true')
    return lookup_parser


@Logger.wrapper
@DataBase.wrapper
def cli(pattern: PurePath, key: str, db: DataBase, porcelain: bool, *args, **kwargs):
    db.logger.print(string(pattern=pattern, db=db, key=key, porcelain=porcelain))


def string(pattern: PurePath, db: DataBase, key: str, porcelain: bool = True) -> str:
    return '\n'.join(strings(pattern=pattern, db=db, key=key, porcelain=porcelain))


def strings(pattern: PurePath, db: DataBase, key: str, porcelain: bool) -> List[str]:
    if key:
        attr_dict = get_dict(db=db, path=pattern, key=key)
        if porcelain:
            for value in attr_dict.values():
                yield str(value)
        else:
            for path, attr in attr_dict.items():
                yield highlight(path, ": ", sep='') + str(attr)
    else:
        if porcelain:
            for entry in db[pattern, ]:
                yield str(entry)
        else:
            yield table.string(pattern, db=db)


def get_dict(db: DataBase, path: PurePath, key: str) -> Dict[PurePath, str]:
    return {entry.path: entry.get(key) for entry in (db[path, ])}
