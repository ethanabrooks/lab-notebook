# stdlib
from typing import Dict, List

# first party
from runs.database import DataBase, add_query_flags
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import PurePath, highlight


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'lookup', help="Lookup specific value associated with database entry.")
    parser.add_argument(
        'key',
        choices=RunEntry.fields() + ('all', ),
        help='Key that value is associated with.')
    add_query_flags(parser, with_sort=True)
    parser.add_argument(
        '--porcelain',
        action='store_true',
        help='Print value only (for use with scripts)')
    return parser


@DataBase.open
@DataBase.query
def cli(runs: List[RunEntry], db: DataBase, logger: Logger, key: str, porcelain: bool,
        *args, **kwargs):
    logger.print(string(runs=runs, key=key, porcelain=porcelain))


def string(runs: List[RunEntry], key: str, porcelain: bool = True) -> str:
    return '\n'.join(strings(runs=runs, key=key, porcelain=porcelain))


def strings(runs: List[RunEntry], key: str, porcelain: bool) -> List[str]:
    if key == 'all':
        for entry in runs:
            yield str(entry)
    else:
        attr_dict = get_dict(runs=runs, key=key)
        if porcelain:
            for value in attr_dict.values():
                yield str(value)
        else:
            for path, attr in attr_dict.items():
                yield highlight(path, ": ", sep='') + str(attr)


def get_dict(runs: List[RunEntry], key: str) -> Dict[PurePath, str]:
    return {entry.path: entry.get(key) for entry in runs}
