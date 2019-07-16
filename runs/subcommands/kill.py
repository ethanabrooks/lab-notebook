# stdlib
from copy import deepcopy
from typing import List

# first party
from runs.arguments import DEFAULT_QUERY_ARGS, add_query_args
from runs.database import DataBase
from runs.run_entry import RunEntry
from runs.transaction.transaction import Transaction


def add_subparser(subparsers):
    parser = subparsers.add_parser("kill", help="Kill selected TMUX sessions.")
    default_args = deepcopy(DEFAULT_QUERY_ARGS)
    default_args["patterns"].update(help="Pattern of runs to kill")
    add_query_args(parser, with_sort=False, default_args=default_args)
    return parser


@Transaction.wrapper
@DataBase.query
def cli(runs: List[RunEntry], transaction: Transaction, *_, **__):
    for path in set(run.path for run in runs):
        transaction.kill(path)
