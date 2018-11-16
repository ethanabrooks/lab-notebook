# stdlib
from copy import deepcopy
from typing import List

# first party
from runs.database import DEFAULT_QUERY_FLAGS, DataBase, add_query_flags
from runs.run_entry import RunEntry
from runs.transaction.transaction import Transaction


def add_subparser(subparsers):
    parser = subparsers.add_parser('kill', help="Kill selected TMUX sessions.")
    default_flags = deepcopy(DEFAULT_QUERY_FLAGS)
    default_flags['patterns'].update(help='Pattern of runs to kill')
    add_query_flags(parser, with_sort=False, default_flags=default_flags)
    return parser


@Transaction.wrapper
@DataBase.query
def cli(runs: List[RunEntry], transaction: Transaction, *args, **kwargs):
    for path in set(run.path for run in runs):
        transaction.kill(path)
