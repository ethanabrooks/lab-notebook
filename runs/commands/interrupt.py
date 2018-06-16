from pathlib import PurePath
from typing import List

from runs.transaction import Transaction


def add_subparser(subparsers):
    interrupt_parser = subparsers.add_parser(
        'interrupt',
        help="Delete runs from the database (and all associated tensorboard "
        "and checkpoint files). Don't worry, the script will ask for "
        "confirmation before deleting anything.")
    interrupt_parser.add_argument(
        'patterns',
        nargs='+',
        help=
        'This script will only delete entries in the database whose names are a complete '
        '(not partial) match of this glob pattern.',
        type=PurePath)
    return interrupt_parser


@Transaction.wrapper
def cli(patterns: List[PurePath], transaction, *args, **kwargs):
    for path in set(run.path for run in transaction.db[patterns]):
        transaction.interrupt(path)