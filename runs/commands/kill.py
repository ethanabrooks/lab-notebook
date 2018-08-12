from typing import List

from runs.transaction.transaction import Transaction
from runs.util import RunPath
from runs.tmux_session import TMUXSession
from runs.shell import Bash


def add_subparser(subparsers):
    parser = subparsers.add_parser('kill', help="Kill selected TMUX sessions.")
    parser.add_argument(
        'patterns',
        nargs='*',
        help=
        'This script will only delete entries in the database whose names are a complete '
        '(not partial) match of this glob pattern.',
        type=RunPath)
    parser.add_argument(
        '--unless', nargs='*', type=RunPath, help='Exclude these paths from the search.')
    parser.add_argument(
        '--active', action='store_true', help='Kill all active runs.')
    return parser


@Transaction.wrapper
def cli(patterns: List[RunPath], unless: List[RunPath], active: bool,
        transaction: Transaction, *args, **kwargs):
    if active:
        tmux = TMUXSession(path='dummy', bash=Bash(transaction.db.logger))
        patterns = [s.replace(',', '%') for s in tmux.list()]
    for path in set(run.path for run in transaction.db.get(patterns, unless=unless)):
        transaction.kill(path)
