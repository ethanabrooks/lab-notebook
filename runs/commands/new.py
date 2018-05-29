import re
from datetime import datetime

from runs.commands import remove
from runs.database import RunEntry, Table
from runs.file_system import FileSystem
from runs.logger import UI, GitBash
from runs.tmux_session import TMUXSession
from runs.util import highlight

from build.lib.runs.util import dirty_repo


@UI.wrapper
@Table.wrapper
def cli(path, prefix, command, description, flags, root, dir_names, ui, table):
    return main(
        path=path,
        prefix=prefix,
        command=command,
        description=description,
        flags=flags,
        bash=GitBash(logger=ui),
        ui=ui,
        table=table,
        tmux=TMUXSession(path=path, logger=ui),
        dir_paths=FileSystem(root=root, dir_names=dir_names).dir_paths(path))


def main(path, prefix, command, description, flags, bash, ui, table, tmux,
         dir_paths):
    # Check if repo is dirty
    if dirty_repo():
        ui.check_permission(
            "Repo is dirty. You should commit before run. Run anyway?")

    if path in table:
        remove.main()

    # create directories
    for path in dir_paths:
        path.mkdir(exist_ok=True, parents=True)

    # process info
    full_command = command
    for flag in flags:
        flag = interpolate_keywords(path, flag)
        full_command += ' ' + flag
    full_command = f'{prefix} {full_command}'

    # prompt = 'Edit the description of this run: (Do not edit the line or above.)'
    # if description is None:
    #     description = string_from_vim(prompt, description)
    if description is None:
        description = ''
    if description == 'commit-message':
        description = bash.cmd('git log -1 --pretty=%B'.split())

    # tmux
    tmux.new(description, full_command)

    # new db entry
    table += RunEntry(
        path=path,
        full_command=full_command,
        commit=bash.last_commit(),
        datetime=datetime.now().isoformat(),
        description=description,
        input_command=command)

    # print result
    ui.print(
        highlight('Description:'),
        description,
        highlight('Command sent to session:'),
        full_command,
        highlight('List active:'),
        'tmux list-session',
        highlight('Attach:'),
        f'tmux attach -t {tmux}',
        sep='\n')


def interpolate_keywords(path, string):
    keywords = dict(path=path, name=path.stem)
    for match in re.findall('.*<(.*)>', string):
        assert match in keywords
    for word, replacement in keywords.items():
        string = string.replace(f'<{word}>', str(replacement))
    return string
