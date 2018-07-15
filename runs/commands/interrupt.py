from typing import List

from runs.transaction.transaction import Transaction
from runs.util import RunPath


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'interrupt',
        help="Delete runs from the database (and all associated tensorboard "
        "and checkpoint files). Don't worry, the script will ask for "
        "confirmation before deleting anything.")
    parser.add_argument(
        'patterns',
        nargs='+',
        help=
        'This script will only delete entries in the database whose names are a complete '
        '(not partial) match of this glob pattern.',
        type=RunPath)
    parser.add_argument(
        '--unless', nargs='*', type=RunPath, help='Exclude these paths from the search.')
    return parser


@Transaction.wrapper
def cli(patterns: List[RunPath], unless: List[RunPath], transaction, *args, **kwargs):
    for path in set(run.path for run in transaction.db.get(patterns, unless=unless)):
        transaction.interrupt(path)
