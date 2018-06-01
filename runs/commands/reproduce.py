from pathlib import PurePath
from typing import List

from runs.database import DataBase
from runs.logger import Logger
from runs.util import highlight


def add_subparser(subparsers):
    reproduce_parser = subparsers.add_parser(
        'reproduce',
        help='Print commands to reproduce a run. This command '
        'does not have side-effects (besides printing).')
    reproduce_parser.add_argument('patterns', nargs='+', type=PurePath)
    reproduce_parser.add_argument(
        '--description',
        type=str,
        default=None,
        help="Description to be assigned to new run. If None, use the same description as "
        "the run being reproduced.")
    reproduce_parser.add_argument(
        '--no-overwrite',
        action='store_true',
        help='If this flag is given, a timestamp will be '
        'appended to any new name that is already in '
        'the database.  Otherwise this entry will '
        'overwrite any entry with the same name. ')
    return reproduce_parser


@Logger.wrapper
@DataBase.wrapper
def cli(patterns: List[PurePath], db: DataBase, *args, **kwargs):
    db.logger.print(string(*patterns, db=db))


def string(*patterns, db: DataBase):
    for entry in db.descendants(*patterns):
        return '\n'.join([
            'To reproduce:',
            highlight(f'git checkout {entry.commit}\n'),
            highlight(
                f"runs new {entry.path} '{entry.input_command}' --description='Reproduce {entry.path}. "
                f"Original description: {entry.description}'")
        ])
