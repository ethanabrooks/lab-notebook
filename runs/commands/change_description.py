from runs.database import DataBase
from runs.logger import Logger
from runs.util import CHDESCRIPTION, PATH, nonempty_string, string_from_vim


def add_subparser(subparsers):
    chdesc_parser = subparsers.add_parser(CHDESCRIPTION, help='Edit description of run.')
    chdesc_parser.add_argument(
        'path',
        help='Name of run whose description you want to edit.',
        type=nonempty_string)
    chdesc_parser.add_argument(
        'description',
        nargs='?',
        default=None,
        help='New description. If None, script will prompt for '
        'a description in Vim')
    return chdesc_parser


@Logger.wrapper
@DataBase.wrapper
def cli(path, description, db, *args, **kwargs):
    entry = db.entry(path)
    if description is None:
        prompt = f"""
Edit description for {entry.path}.
Command: {entry.full_command}
"""
        description = string_from_vim(prompt, entry.description)
    db.update(entry.path, description=description)
