from typing import Dict, List, Optional

from runs.commands import table
from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import RunPath, highlight


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'lookup', help='Lookup specific value associated with database entry')
    parser.add_argument(
        'key',
        choices=RunEntry.fields() + ('all', ),
        help='Key that value is associated with.')
    parser.add_argument(
        'patterns',
        help='Pattern of runs for which to retrieve key.',
        type=RunPath,
        nargs='*')
    parser.add_argument(
        '--unless', nargs='*', type=RunPath, help='Exclude these paths from the search.')
    parser.add_argument(
        '--porcelain',
        action='store_true',
        help='Print value only (for use with scripts)')
    return parser


@Logger.wrapper
@DataBase.wrapper
def cli(patterns: List[RunPath], unless: List[RunPath], key: str, db: DataBase,
        porcelain: bool, *args, **kwargs):
    db.logger.print(string(*patterns, unless=unless, db=db, key=key, porcelain=porcelain))


def string(*patterns,
           unless: List[RunPath] = None,
           db: DataBase,
           key: str,
           porcelain: bool = True) -> str:
    return '\n'.join(
        strings(*patterns, unless=unless, db=db, key=key, porcelain=porcelain))


def strings(*patterns, unless: Optional[List[RunPath]], db: DataBase, key: str,
            porcelain: bool) -> List[str]:
    if key == 'all':
        if porcelain:
            for entry in db.get(patterns, unless=unless):
                yield str(entry)
        else:
            yield table.string(*patterns, unless=unless, db=db)
    else:
        attr_dict = get_dict(*patterns, unless=unless, db=db, key=key)
        if porcelain:
            for value in attr_dict.values():
                yield str(value)
        else:
            for path, attr in attr_dict.items():
                yield highlight(path, ": ", sep='') + str(attr)


def get_dict(*pattern, unless: List[RunPath], db: DataBase,
             key: str) -> Dict[RunPath, str]:
    return {entry.path: entry.get(key) for entry in (db.get(pattern, unless=unless))}
