from typing import Optional

from runs.transaction.transaction import Transaction
from runs.util import RunPath


def add_subparser(subparsers):
    parser = subparsers.add_parser('change-description', help='Edit description of run.')
    parser.add_argument(
        'path', help='Name of run whose description you want to edit.', type=RunPath)
    parser.add_argument(
        'description',
        nargs='?',
        default=None,
        help='New description. If None, script will prompt for '
        'a description in Vim')
    return parser


@Transaction.wrapper
def cli(transaction: Transaction, path: RunPath, description: Optional[str], *args,
        **kwargs):
    entry = transaction.db.entry(path)
    transaction.change_description(
        path=entry.path,
        command=entry.command,
        old_description=entry.description,
        new_description=description)
