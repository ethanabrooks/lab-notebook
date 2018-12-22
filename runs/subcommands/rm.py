# stdlib
from copy import deepcopy
from typing import List

# first party
from runs.database import DataBase
from runs.run_entry import RunEntry
from runs.transaction.transaction import Transaction
from runs.arguments import DEFAULT_QUERY_ARGS, add_query_args


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'rm',
        help="Delete runs from the database (and all associated tensorboard "
        "and checkpoint files).")
    default_args = deepcopy(DEFAULT_QUERY_ARGS)
    default_args['patterns'].update(
        help=
        'This script will only delete entries in the database whose names are a complete '
        '(not partial) match of this sql pattern.')
    add_query_args(parser, with_sort=False, default_args=default_args)
    return parser


@Transaction.wrapper
@DataBase.query
def cli(runs: List[RunEntry], transaction, *_, **__):
    for path in set(run.path for run in runs):
        transaction.remove(path)
