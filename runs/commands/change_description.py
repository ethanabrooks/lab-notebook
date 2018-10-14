from copy import copy
from pathlib import PurePath
from typing import Optional, List

from runs.database import DEFAULT_QUERY_FLAGS, add_query_flags, DataBase
from runs.run_entry import RunEntry
from runs.transaction.transaction import Transaction


def add_subparser(subparsers):
    parser = subparsers.add_parser('change-description', help='Edit description of run.')
    default_flags = copy(DEFAULT_QUERY_FLAGS)
    default_flags['patterns'].update(help='Name of run whose description you want to edit.')
    add_query_flags(parser, with_sort=False, default_flags=default_flags)
    parser.add_argument(
        'description',
        nargs='?',
        default=None,
        help='New description. If None, script will prompt for a description in Vim')
    return parser


@DataBase.query
@Transaction.wrapper
def cli(transaction: Transaction, runs: List[RunEntry], description: Optional[str], *args,
        **kwargs):
    for run in runs:
        transaction.change_description(
            paths=run.path,
            command=run.command,
            old_description=run.description,
            new_description=description)
