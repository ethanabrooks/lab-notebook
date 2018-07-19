from typing import List

from runs.transaction.transaction import Transaction
from runs.util import RunPath


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'rm',
        help="Delete runs from the database (and all associated tensorboard "
        "and checkpoint files).")
    parser.add_argument(
        'patterns',
        nargs='+',
        help=
        'This script will only delete entries in the database whose names are a complete '
        '(not partial) match of this sql pattern.',
        type=RunPath)
    parser.add_argument(
        '--unless',
        nargs='*',
        type=RunPath,
        help='Print list of path names without tree '
        'formatting.')
    return parser


@Transaction.wrapper
def cli(patterns: List[RunPath], unless: List[RunPath], transaction, *args, **kwargs):
    for path in set(run.path for run in transaction.db.get(patterns, unless=unless)):
        transaction.remove(path)
