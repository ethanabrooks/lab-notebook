from runs.database import Table
from runs.file_system import FileSystem
from runs.logger import UI
from runs.tmux_session import TMUXSession


@UI.wrapper
@Table.wrapper
def cli(pattern, root, dir_names, ui, table):
    entries = table[pattern]
    ui.check_permission(
        "Runs to be removed:",
        *[e.path for e in entries],
        "Continue?",
        sep='\n')
    file_system = FileSystem(root=root, dir_names=dir_names)
    for entry in table[pattern]:
        execute(
            path=entry.path, table=table, file_system=file_system, logger=ui)


def execute(path, table, logger, file_system):
    TMUXSession(path, logger=logger).kill()
    file_system.rmdirs(path)
    del table[path]
