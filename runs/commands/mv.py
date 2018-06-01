from itertools import zip_longest
from pathlib import PurePath

from runs.commands import rm
from runs.database import DataBase
from runs.file_system import FileSystem
from runs.logger import UI
from runs.shell import Bash
from runs.tmux_session import TMUXSession

path_clarification = ' Can be a relative path from runs: `DIR/NAME|PATTERN` Can also be a pattern. '


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'mv',
        help='Move a run from OLD to NEW. '
        'Functionality is identical to `mkdir -p` except that non-existent dirs'
        'are created and empty dirs are removed automatically'
        'The program will show you planned '
        'moves and ask permission before changing anything.')
    parser.add_argument(
        'source',
        nargs='+',
        help='Name of run to rename.' + path_clarification,
        type=PurePath)
    parser.add_argument(
        'destination', help='New name for run.' + path_clarification, type=PurePath)
    parser.add_argument(
        '--kill-tmux',
        action='store_true',
        help='Kill tmux session instead of renaming it.')
    return parser


@UI.wrapper
@DataBase.wrapper
def cli(source, destination, kill_tmux, db, root, dir_names, *args, **kwargs):
    logger = db.logger
    move(
        *source,
        db=db,
        dest_path=destination,
        kill_tmux=kill_tmux,
        ui=logger,
        file_system=FileSystem(root=root, dir_names=dir_names))


def move(*src_patterns, db: DataBase, dest_path: str, kill_tmux: bool, ui: UI,
         file_system: FileSystem):
    moves = dict()
    for src_pattern in src_patterns:
        src_entries = db.descendants(src_pattern)

        if dest_path in db and len(src_entries) > 1:
            ui.exit(
                f"'{dest_path}' already exists and '{src_pattern}' matches the following runs:",
                *[e.path for e in src_entries],
                "Cannot move multiple runs into an existing "
                "run.",
                sep='\n')

        def is_dir(pattern):
            return pattern == PurePath('.') or f'{pattern}/%' in db

        def get_dest(src_path: PurePath) -> PurePath:
            if is_dir(src_pattern):
                if is_dir(dest_path) or len(src_entries) > 1:
                    old_parts = PurePath(src_pattern).parent.parts
                    src_parts = PurePath(src_path).parts
                    return PurePath(
                        dest_path, *[
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

        for entry in src_entries:
            moves[entry.path] = get_dest(PurePath(entry.path))

    # check before moving
    ui.check_permission('\n'.join(
        ["Planned moves:", *[f"{s} -> {d}" for s, d in moves.items()], 'Continue?']))

    # check for conflicts with existing runs

    existing_runs = [d for d in moves.values() if d in db]
    if existing_runs:
        ui.check_permission('Runs to be removed:', *existing_runs, 'Continue?')
    for src_path, dest_path in moves.items():
        if src_path != dest_path:
            if dest_path in db:
                rm.remove(path=dest_path, db=db, logger=ui, file_system=file_system)

            # Move individual run
            file_system.mvdirs(src_path, dest_path)

            tmux = TMUXSession(path=src_path, bash=Bash(logger=ui))
            if kill_tmux:
                tmux.kill()
            else:
                tmux.rename(dest_path)
            db.update(src_path, path=dest_path)
