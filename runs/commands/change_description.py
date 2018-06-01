from pathlib import PurePath

from runs.database import DataBase
from runs.logger import Logger
from runs.util import string_from_vim


def add_subparser(subparsers):
    chdesc_parser = subparsers.add_parser(
        'change-description', help='Edit description of run.')
    chdesc_parser.add_argument(
        'path', help='Name of run whose description you want to edit.', type=PurePath)
    chdesc_parser.add_argument(
        'description',
        nargs='?',
        default=None,
        help='New description. If None, script will prompt for '
        'a description in Vim')
    return chdesc_parser


@Logger.wrapper
@DataBase.wrapper
def cli(path: PurePath, description: str, db: DataBase, *args, **kwargs):
    entry = db.entry(path)
    if description is None:
        prompt = f"""
Edit description for {entry.path}.
Command: {entry.full_command}
"""
        description = string_from_vim(prompt, entry.description)
    db.update(entry.path, description=description)
