# stdlib
from copy import deepcopy
from typing import List, Optional

# first party
from runs.database import DEFAULT_QUERY_FLAGS, DataBase, add_query_flags
from runs.run_entry import RunEntry
from runs.transaction.transaction import Transaction


def add_subparser(subparsers):
    parser = subparsers.add_parser('change-description', help='Edit description of run.')
    default_flags = deepcopy(DEFAULT_QUERY_FLAGS)
    default_flags['patterns'].update(
        help='Name of run whose description you want to edit.')
    add_query_flags(parser, with_sort=False, default_flags=default_flags)
    parser.add_argument('description', help='New description to assign to paths')
    return parser


@Transaction.wrapper
@DataBase.query
def cli(transaction: Transaction, runs: List[RunEntry], description: Optional[str], *args,
        **kwargs):
    for run in runs:
        transaction.change_description(
            path=run.path,
            command=run.command,
            old_description=run.description,
            new_description=description)
