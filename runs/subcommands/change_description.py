# stdlib
from copy import deepcopy
from typing import List, Optional

# first party
from runs.arguments import DEFAULT_QUERY_ARGS, add_query_args
from runs.database import DataBase
from runs.run_entry import RunEntry
from runs.transaction.transaction import Transaction


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "change-description", help="Edit description of run."
    )
    default_args = deepcopy(DEFAULT_QUERY_ARGS)
    default_args["patterns"].update(
        help="Name of run whose description you want to edit."
    )
    add_query_args(parser, with_sort=False, default_args=default_args)
    parser.add_argument("description", help="New description to assign to paths")
    return parser


@Transaction.wrapper
@DataBase.query
def cli(
    transaction: Transaction, runs: List[RunEntry], description: Optional[str], *_, **__
):
    for run in runs:
        transaction.change_description(
            path=run.path,
            command=run.command,
            old_description=run.description,
            new_description=description,
        )
