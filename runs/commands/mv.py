from collections import defaultdict
from copy import copy
from itertools import zip_longest
from pathlib import PurePath
from typing import List

from runs.database import DataBase, QueryArgs
from runs.transaction.transaction import Transaction
from runs.util import PurePath
from runs.database import add_query_flags, DEFAULT_QUERY_FLAGS

path_clarification = ' Can be a relative path from runs: `DIR/NAME|PATTERN` Can also be a pattern. '


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'mv',
        help='Move a run from OLD to NEW. '
             'Functionality is identical to Linux `mv` except that non-existent dirs'
             'are created and empty dirs are removed automatically.')

    default_flags = copy(DEFAULT_QUERY_FLAGS)
    del default_flags['--descendants']
    add_query_flags(parser, with_sort=False, default_flags=default_flags)

    parser.add_argument(
        '--no-descendants',
        dest='descendants',
        action='store_false',
        help="Don't move descendants of search pattern.")
    parser.add_argument(
        'destination', help='New name for run.' + path_clarification, type=PurePath)
    parser.add_argument(
        '--kill-tmux',
        action='store_true',
        help='Kill tmux session instead of renaming it.')
    return parser


@Transaction.wrapper
@DataBase.bundle_query_args
def cli(query_args: QueryArgs, destination: PurePath, kill_tmux: bool, transaction: Transaction,
        db: DataBase, *args, **kwargs):
    move(
        query_args=query_args,
        db=db,
        dest_path=destination,
        kill_tmux=kill_tmux,
        transaction=transaction)


def move(query_args: QueryArgs, dest_path: str, kill_tmux: bool,
         transaction: Transaction, db: DataBase):
    dest_path_is_dir = any([dest_path == PurePath('.'),
                            f'{dest_path}/%' in db,
                            str(dest_path).endswith('/')])
    if dest_path_is_dir:
        dest_path = str(dest_path) + '/'

    for src_pattern in query_args.patterns:
        src_to_dest = defaultdict(list)
        src_entries = db.get(**query_args._replace(patterns=[src_pattern])._asdict())
        part_to_replace = src_pattern  # TODO
        if dest_path_is_dir:
            part_to_replace = str(src_pattern.parent) + '/'
        for entry in src_entries:
            src_to_dest[entry.path] += [
                str(entry.path).replace(str(part_to_replace),str(dest_path))]

        for src, dests in src_to_dest.items():
            for i, dest in enumerate(dests):
                if len(dests) > 1:
                    dest = PurePath(dest, str(i))
                else:
                    dest = PurePath(dest)
                transaction.move(src=src, dest=dest, kill_tmux=kill_tmux)
                if dest in db:
                    transaction.remove(dest)

    def save():
        def is_dir(pattern):
            return pattern == PurePath('.') or \
                   f'{PurePath(pattern)}/%' in db

        for entry in src_entries:
            src_path = PurePath(entry.path)
            if is_dir(src_pattern):
                if is_dir(dest_path) or len(src_entries) > 1:
                    old_parts = PurePath(src_pattern).parent.parts
                    src_parts = PurePath(src_path).parts
                    dest = PurePath(
                        dest_path, *[
                            p for p, from_old in zip_longest(src_parts, old_parts)
                            if not from_old
                        ])
                else:
                    dest = PurePath(dest_path, PurePath(src_path).name)
            else:
                if is_dir(dest_path) or len(src_entries) > 1:
                    dest = PurePath(dest_path, PurePath(src_path).name)
                else:
                    dest = PurePath(dest_path)

            transaction.move(src=entry.path, dest=dest, kill_tmux=kill_tmux)
            if dest in db:
                transaction.remove(dest)
