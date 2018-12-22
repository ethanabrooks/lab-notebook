# stdlib

# first party
from runs.command import Command, Type
from runs.database import DataBase
from runs.util import GREEN, RED, RESET, PurePath


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'diff',
        help='Compare commands associated with two '
        'runs, highlighting additions in the '
        'first in green and deletions from the '
        'second in red.')
    parser.add_argument('path1', type=PurePath, help='Path to compare with path2')
    parser.add_argument('path2', type=PurePath, help='Path to compare with path1')
    return parser


@DataBase.open
def cli(db: DataBase, path1: PurePath, path2: PurePath, *_, **__):
    c1 = Command.from_db(db, path1)
    c2 = Command.from_db(db, path2)
    for element, blob_type in c1.diff(c2):
        if blob_type == Type.ADDED:
            print(GREEN, element, RESET, end='')
        if blob_type == Type.DELETED:
            print(RED, element, RESET, end='')
        if blob_type == Type.UNCHANGED:
            print(element, end=' ')
