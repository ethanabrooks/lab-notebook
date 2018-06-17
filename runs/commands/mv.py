from itertools import zip_longest
from pathlib import PurePath
from typing import List

from runs.transaction.transaction import Transaction
from runs.util import RunPath

path_clarification = ' Can be a relative path from runs: `DIR/NAME|PATTERN` Can also be a pattern. '


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'mv',
        help='Move a run from OLD to NEW. '
        'Functionality is identical to `mkdir -p` except that non-existent dirs'
        'are created and empty dirs are removed automatically'
        'The program will show you planned '
        'moves and ask permission before changing anything.')
    parser.add_argument(
        'source',
        nargs='+',
        help='Name of run to rename.' + path_clarification,
        type=RunPath)
    parser.add_argument(
        '--unless',
        nargs='*',
        type=RunPath,
        help='Print list of path names without tree '
             'formatting.')
    parser.add_argument(
        'destination', help='New name for run.' + path_clarification, type=RunPath)
    parser.add_argument(
        '--kill-tmux',
        action='store_true',
        help='Kill tmux session instead of renaming it.')
    return parser


@Transaction.wrapper
def cli(source, unless, destination, kill_tmux, transaction, *args, **kwargs):
    move(*source, unless=unless, dest_path=destination, kill_tmux=kill_tmux, transaction=transaction)


def move(*src_patterns, unless: List[RunPath], dest_path: str, kill_tmux: bool, transaction: Transaction):
    db = transaction.db
    for src_pattern in src_patterns:
        src_entries = db.descendants(src_pattern, unless=unless)

        def is_dir(pattern):
            return pattern == RunPath('.') or \
                   f'{PurePath(pattern)}/%' in db

        for entry in src_entries:
            src_path = RunPath(entry.path)
            if is_dir(src_pattern):
                if is_dir(dest_path) or len(src_entries) > 1:
                    old_parts = RunPath(src_pattern).parent.parts
                    src_parts = RunPath(src_path).parts
                    dest = PurePath(
                        dest_path, *[
                            p for p, from_old in zip_longest(src_parts, old_parts)
                            if not from_old
                        ])
                else:
                    dest = PurePath(dest_path, RunPath(src_path).name)
            else:
                if is_dir(dest_path) or len(src_entries) > 1:
                    dest = PurePath(dest_path, RunPath(src_path).name)
                else:
                    dest = PurePath(dest_path)

            transaction.move(src=entry.path, dest=dest, kill_tmux=kill_tmux)
            if dest in db:
                transaction.remove(dest)
