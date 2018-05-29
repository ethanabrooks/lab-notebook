from itertools import zip_longest
from pathlib import PurePath

from runs.commands import rm
from runs.database import Table
from runs.file_system import FileSystem
from runs.logger import UI
from runs.shell import Bash
from runs.tmux_session import TMUXSession
from runs.util import MOVE, ROOT_PATH, SEP, nonempty_string


def add_move_parser(path_clarification, subparsers):
    parser = subparsers.add_parser(
        MOVE,
        help='Move a run from OLD to NEW. '
        'Functionality is identical to `mkdir -p` except that non-existent dirs'
        'are created and empty dirs are removed automatically'
        'The program will show you planned '
        'moves and ask permission before changing anything.')
    parser.add_argument(
        'source',
        help='Name of run to rename.' + path_clarification,
        type=nonempty_string)
    parser.add_argument(
        'destination',
        help='New name for run.' + path_clarification,
        type=nonempty_string)
    parser.add_argument(
        '--kill-tmux',
        action='store_true',
        help='Kill tmux session instead of renaming it.')
    return parser


@UI.wrapper
@Table.wrapper
def cli(source, destination, kill_tmux, table, root, dir_names, *args,
        **kwargs):
    logger = table.logger
    move(
        table=table,
        src_pattern=source,
        dest_path=destination,
        tmux=TMUXSession(source, bash=Bash(logger=logger)),
        kill_tmux=kill_tmux,
        ui=logger,
        file_system=FileSystem(root=root, dir_names=dir_names))


def move(table: Table, src_pattern: str, dest_path: str, tmux: TMUXSession,
         kill_tmux: bool, ui: UI, file_system: FileSystem):
    src_entries = table[f'{src_pattern}%']

    if dest_path in table and len(src_entries) > 1:
        ui.exit(
            f"'{dest_path}' already exists and '{src_pattern}' matches the following runs:",
            *[e.path for e in src_entries],
            "Cannot move multiple runs into an existing "
            "run.",
            sep='\n')

    def is_dir(pattern):
        return pattern == ROOT_PATH or f'{pattern.rstrip(SEP)}{SEP}%' in table

    def get_dest(src_path) -> PurePath:
        if is_dir(src_pattern):
            if is_dir(dest_path) or len(src_entries) > 1:
                old_parts = PurePath(src_pattern).parent.parts
                src_parts = PurePath(src_path).parts
                return PurePath(dest_path, *[
                    p for p, from_old in zip_longest(src_parts, old_parts)
                    if not from_old
                ])
            else:
                return PurePath(dest_path, PurePath(src_path).stem)
        else:
            if is_dir(dest_path) or len(src_entries) > 1:
                return PurePath(dest_path, PurePath(src_path).stem)
            else:
                return PurePath(dest_path)

    moves = {s.path: get_dest(s.path) for s in src_entries}

    # check before moving
    ui.check_permission("Planned moves:",
                        *[f"{s} -> {d}" for s, d in moves.items()],
                        'Continue?')

    # check for conflicts with existing runs

    existing_runs = [d for d in moves.values() if d in table]
    if existing_runs:
        ui.check_permission('Runs to be removed:', *existing_runs, 'Continue?')
    for src_path, dest_path in moves.items():
        if src_path != dest_path:
            if dest_path in table:
                rm.remove(
                    path=dest_path,
                    table=table,
                    logger=ui,
                    file_system=file_system)

            # Move individual run
            file_system.mvdirs(src_path, dest_path)
            if kill_tmux:
                tmux.kill()
            else:
                tmux.rename(dest_path)
            table.update(src_path, path=dest_path)
