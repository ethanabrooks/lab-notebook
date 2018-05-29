from runs.database import Table
from runs.file_system import FileSystem
from runs.logger import UI, Bash
from runs.tmux_session import TMUXSession
from runs.util import REMOVE, PATTERN, nonempty_string


@UI.wrapper
@Table.wrapper
def cli(pattern, root, dir_names, logger, table,
        *args, **kwargs):
    entries = table[pattern]
    logger.check_permission(
        "Runs to be removed:",
        *[e.path for e in entries],
        "Continue?",
        sep='\n')
    file_system = FileSystem(root=root, dir_names=dir_names)
    for entry in table[pattern]:
        execute(
            path=entry.path, table=table, file_system=file_system, logger=logger)


def execute(path, table, logger, file_system):
    TMUXSession(path, bash=Bash(logger=logger)).kill()
    file_system.rmdirs(path)
    del table[path]


def add_remove_parser(subparsers):
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