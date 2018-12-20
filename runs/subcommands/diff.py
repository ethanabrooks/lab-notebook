# stdlib

# first party
from runs.command import Command, Type
from runs.database import DataBase
from runs.util import GREEN, RED, RESET, PurePath


def add_subparser(subparsers):
    parser = subparsers.add_parser('diff', help='Rank flags by Pearson correlation.')
    parser.add_argument('path1', type=PurePath, help='Path to compare with path2')
    parser.add_argument('path2', type=PurePath, help='Path to compare with path1')
    return parser


@DataBase.open
def cli(db: DataBase, path1: PurePath, path2: PurePath, *args, **kwargs):
    def command(path):
        run, = db[path]
        return Command(run.command, path=path)

    c1 = command(path1)
    c2 = command(path2)
    for element, blob_type in c1.diff(c2):
        if blob_type == Type.ADDED:
            print(GREEN, element, RESET, end='')
        if blob_type == Type.DELETED:
            print(RED, element, RESET, end='')
        if blob_type == Type.UNCHANGED:
            print(element, end=' ')
