from pathlib import PurePath
from typing import Optional

from runs.transaction.transaction import Transaction


def add_subparser(subparsers):
    chdesc_parser = subparsers.add_parser(
        'change-description', help='Edit description of run.')
    chdesc_parser.add_argument(
        'path', help='Name of run whose description you want to edit.', type=PurePath)
    chdesc_parser.add_argument(
        'description',
        nargs='?',
        default=None,
        help='New description. If None, script will prompt for '
        'a description in Vim')
    return chdesc_parser


@Transaction.wrapper
def cli(transaction: Transaction, path: PurePath, description: Optional[str], *args,
        **kwargs):
    entry = transaction.db.entry(path)
    transaction.change_description(
        path=entry.path,
        full_command=entry.full_command,
        old_description=entry.description,
        new_description=description)
