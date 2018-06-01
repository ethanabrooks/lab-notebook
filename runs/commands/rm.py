from runs.database import DataBase
from runs.file_system import FileSystem
from runs.logger import UI
from runs.shell import Bash
from runs.tmux_session import TMUXSession
from runs.util import PATTERN, REMOVE, nonempty_string


def add_subparser(subparsers):
    remove_parser = subparsers.add_parser(
        REMOVE,
        help="Delete runs from the database (and all associated tensorboard "
             "and checkpoint files). Don't worry, the script will ask for "
             "confirmation before deleting anything.")
    remove_parser.add_argument(
        'patterns',
        nargs='*',
        help=
        'This script will only delete entries in the database whose names are a complete '
        '(not partial) match of this glob pattern.',
        type=nonempty_string)
    return remove_parser


@UI.wrapper
@DataBase.wrapper
def cli(patterns, root, dir_names, db, *args, **kwargs):
    logger = db.logger
    file_system = FileSystem(root=root, dir_names=dir_names)
    remove_with_check(*patterns, db=db, logger=logger, file_system=file_system)


def remove_with_check(*patterns, db, logger, file_system):
    entries = [entry for pattern in patterns
               for entry in db[pattern + '%']]
    logger.check_permission('\n'.join(
        ["Runs to be removed:", *[str(e.path) for e in entries], "Continue?"]))
    for entry in entries:
        remove(path=entry.path, db=db, file_system=file_system, logger=logger)


def remove(path, db, logger, file_system):
    TMUXSession(path, bash=Bash(logger=logger)).kill()
    file_system.rmdirs(path)
    del db[path]
