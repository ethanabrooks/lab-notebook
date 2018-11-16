# stdlib
from collections import defaultdict
from copy import deepcopy
import sqlite3

# first party
from runs.database import DEFAULT_QUERY_FLAGS, DataBase, QueryArgs, add_query_flags
from runs.transaction.transaction import Transaction
from runs.util import PurePath

path_clarification = ' Can be a relative path from runs: `DIR/NAME|PATTERN` Can also be a pattern. '


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'mv',
        help='Move a run from OLD to NEW. '
        'Functionality is identical to Linux `mv` except that non-existent dirs'
        'are created and empty dirs are removed automatically.')

    default_flags = deepcopy(DEFAULT_QUERY_FLAGS)
    del default_flags['--descendants']
    add_query_flags(parser, with_sort=False, default_flags=default_flags)

    parser.add_argument(
        '--no-descendants',
        dest='descendants',
        action='store_false',
        help="Don't move descendants of search pattern.")
    parser.add_argument(
        'destination', help='New name for run.' + path_clarification, type=str)
    parser.add_argument(
        '--kill-tmux',
        action='store_true',
        help='Kill tmux session instead of renaming it.')
    return parser


@Transaction.wrapper
@DataBase.query
def cli(query_args: QueryArgs, destination: str, kill_tmux: bool,
        transaction: Transaction, db: DataBase, *args, **kwargs):
    move(
        query_args=query_args,
        db=db,
        dest_path=destination,
        kill_tmux=kill_tmux,
        transaction=transaction)


def move(query_args: QueryArgs, dest_path: str, kill_tmux: bool, transaction: Transaction,
         db: DataBase):
    dest_path_is_dir = any(
        [dest_path == '.', f'{dest_path}/%' in db,
         dest_path.endswith('/')])

    for src_pattern in query_args.patterns:
        dest_to_src = defaultdict(list)
        src_entries = db.get(**query_args._replace(patterns=[src_pattern])._asdict())

        for entry in src_entries:

            # parent, grandparent, great-grandparent, etc.
            parents = [str(entry.path)] + [str(p) + '/' for p in entry.path.parents]
            matches = [
                p for p in reversed(parents) if like(str(p),
                                                     str(src_pattern) + '%')
            ]

            head = next(iter(matches))  # a/b/% -> a/b
            tail = PurePath(*[PurePath(m).name for m in matches])  # a/b/% -> c/d

            if dest_path_is_dir:
                dest = PurePath(dest_path, tail)
            else:
                dest = str(entry.path).replace(head.rstrip('/'), dest_path, 1)
            dest_to_src[dest] += [entry.path]

        for dest, srcs in dest_to_src.items():
            for i, src in enumerate(srcs):
                if len(srcs) > 1:
                    dest = PurePath(dest, str(i))
                else:
                    dest = PurePath(dest)
                transaction.move(src=src, dest=dest, kill_tmux=kill_tmux)
                if dest in db:
                    transaction.remove(dest)


def like(a: str, b: str) -> bool:
    conn = sqlite3.connect(":memory:")
    try:
        c = conn.cursor()
        c.execute("SELECT ? LIKE ?", (a, b))
        result, = c.fetchone()
        return bool(result)
    finally:
        conn.close()
