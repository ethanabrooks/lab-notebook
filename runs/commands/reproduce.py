import re
from typing import List

from runs.database import DataBase
from runs.logger import Logger
from runs.util import RunPath, highlight, interpolate_keywords


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'reproduce',
        help='Print commands to reproduce a run. This command '
        'does not have side-effects (besides printing).')
    parser.add_argument('patterns', nargs='+', type=RunPath)
    parser.add_argument(
        '--description',
        type=str,
        default=None,
        help="Description to be assigned to new run. If None, use the same description as "
        "the run being reproduced.")
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Without this flag, runs paths either get a number appended to them or '
        'have an existing number incremented. With this flag, the reproduced run '
        'just gets overwritten.')
    parser.add_argument(
        '--unless',
        nargs='*',
        type=RunPath,
        help='Print list of path names without tree '
        'formatting.')
    return parser


@Logger.wrapper
@DataBase.wrapper
def cli(patterns: List[RunPath], unless: List[RunPath], db: DataBase,
        flags: List[str], prefix: str, overwrite: bool, *args, **kwargs):
    db.logger.print(
        string(*patterns, unless=unless, db=db, flags=flags, prefix=prefix,
               overwrite=overwrite))


def string(*patterns, unless: List[RunPath], db: DataBase,
           flags: List[str], prefix: str, overwrite: bool):
    for entry in db.descendants(*patterns, unless=unless):
        new_path = str(entry.path)
        if not overwrite:
            pattern = re.compile('(.*\.)(\d*)')
            endswith_number = pattern.match(str(entry.path))
            while new_path in db:
                if endswith_number:
                    trailing_number = int(endswith_number[2]) + 1
                    new_path = endswith_number[1] + str(trailing_number)
                else:
                    new_path += '.1'

        flags = [interpolate_keywords(entry.path, f) for f in flags]
        command = entry.command
        for s in flags + [prefix]:
            command = command.replace(s, '')
        return '\n'.join([
            highlight('To reproduce:'), f'git checkout {entry.commit}\n',
            f"runs new {new_path} '{command}' --description='Reproduce {entry.path}. "
            f"Original description: {entry.description}'"
        ])
