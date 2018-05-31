import shutil

from runs.database import Table
from runs.logger import UI
from runs.util import nonempty_string


def add_subparser(subparsers):
    parser = subparsers.add_parser('killall', help='Destroy all runs.')
    parser.add_argument(
        '--assume-yes',
        '-y',
        action='store_true',
        help='Don\'t ask permission before performing operations.')
    parser.add_argument(
        '--root',
        help='Custom path to directory where config directories (if any) are automatically '
        'created',
        type=nonempty_string)
    return parser


@UI.wrapper
@Table.wrapper
def cli(table, root, *args, **kwargs):
    runs = [e.path for e in table.all()]
    table.logger.check_permission('\n'.join(
        map(str, ["Runs to be removed:", *runs, "Continue?"])))
    table.delete()
    table.path.unlink()
    shutil.rmtree(str(root), ignore_errors=True)
