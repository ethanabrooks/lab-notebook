# stdlib
from copy import deepcopy
from typing import List

# first party
from runs.database import DEFAULT_QUERY_FLAGS, DataBase, add_query_flags
from runs.run_entry import RunEntry
from runs.transaction.transaction import Transaction


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'rm',
        help="Delete runs from the database (and all associated tensorboard "
        "and checkpoint files).")
    default_flags = deepcopy(DEFAULT_QUERY_FLAGS)
    default_flags['patterns'].update(
        help=
        'This script will only delete entries in the database whose names are a complete '
        '(not partial) match of this sql pattern.')
    add_query_flags(parser, with_sort=False, default_flags=default_flags)
    return parser


@Transaction.wrapper
@DataBase.query
def cli(runs: List[RunEntry], transaction, *args, **kwargs):
    for path in set(run.path for run in runs):
        transaction.remove(path)
