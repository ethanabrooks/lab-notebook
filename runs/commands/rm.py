from runs.database import DataBase
from runs.file_system import FileSystem
from runs.logger import UI
from runs.shell import Bash
from runs.tmux_session import TMUXSession
from runs.util import PATTERN, REMOVE, nonempty_string


@UI.wrapper
@DataBase.wrapper
def cli(pattern, root, dir_names, db, *args, **kwargs):
    entries = db[pattern]
    logger = db.logger
    logger.check_permission('\n'.join(
        ["Runs to be removed:", *[str(e.path) for e in entries], "Continue?"]))
    file_system = FileSystem(root=root, dir_names=dir_names)
    for entry in db[pattern]:
        remove(path=entry.path, db=db, file_system=file_system, logger=logger)


def remove(path, db, logger, file_system):
    TMUXSession(path, bash=Bash(logger=logger)).kill()
    file_system.rmdirs(path)
    del db[path]


def add_subparser(subparsers):
    remove_parser = subparsers.add_parser(
        REMOVE,
        help="Delete runs from the database (and all associated tensorboard "
        "and checkpoint files). Don't worry, the script will ask for "
        "confirmation before deleting anything.")
    remove_parser.add_argument(
        PATTERN,
        help=
        'This script will only delete entries in the database whose names are a complete '
        '(not partial) match of this glob pattern.',
        type=nonempty_string)
    return remove_parser
