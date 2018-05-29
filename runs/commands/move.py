from itertools import zip_longest
from pathlib import PurePath

from runs.commands import remove
from runs.database import Table
from runs.file_system import FileSystem
from runs.logger import UI
from runs.tmux_session import TMUXSession
from runs.util import ROOT_PATH


@UI.wrapper
@Table.wrapper
def cli(src, dest, kill_tmux, table, ui):
    move(
        table=table,
        src_pattern=src,
        dest_path=dest,
        kill_tmux=kill_tmux,
        ui=ui)


def move(table: Table, src_pattern: str, dest_path: str, tmux: TMUXSession,
         kill_tmux: bool, ui: UI, file_system: FileSystem):
    src_entries = table[f'{src_pattern}%']

    if dest_path in table and len(src_entries) > 1:
        ui.exit(
            f"'{dest_path}' already exists and '{src_pattern}' matches the following runs:",
            *src_entries,
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
    # noinspection PyUnresolvedReferences
    ui.check_permission(
        "Planned moves:",
        *[f"{s.path} -> {d.path}" for s, d in moves.items()],
        'Continue?',
        sep='\n')

    # check for conflicts with existing runs
    ui.check_permission(
        'Runs to be removed:',
        *[d.path for d in moves.values() if d.exists()],
        'Continue?',
        sep='\n')
    for src_path, dest_path in moves.items():
        if src_path != dest_path:
            if dest_path in table:
                remove.execute(
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
