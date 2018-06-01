from pathlib import Path

from runs.transaction import Transaction


def add_subparser(subparsers):
    parser = subparsers.add_parser('killall', help='Destroy all runs.')
    parser.add_argument(
        '--root',
        help='Custom path to directory where config directories (if any) are automatically '
        'created',
        type=Path)
    return parser


@Transaction.wrapper
def cli(transaction: Transaction, *args, **kwargs):
    for entry in transaction.db.all():
        transaction.removals.add(entry.path)
