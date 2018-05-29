import re
from datetime import datetime
from pathlib import PurePath, Path
from typing import Optional

from build.lib.runs.util import dirty_repo
from runs.commands import remove
from runs.database import RunEntry, Table
from runs.file_system import FileSystem
from runs.logger import UI, GitBash, Bash
from runs.tmux_session import TMUXSession
from runs.util import highlight, PATH, nonempty_string


def add_new_parser(subparsers):
    parser = subparsers.add_parser('new', help='Start a new run.')
    parser.add_argument(
        PATH,
        help='Unique path assigned to new run. "\\"-delimited.',
        type=nonempty_string)
    parser.add_argument(
        'command',
        help='Command that will be run in tmux.',
        type=nonempty_string)
    parser.add_argument(
        '--description',
        help='Description of this run. Explain what this run was all about or '
             'just write whatever your heart desires. If this argument is `commit-message`,'
             'it will simply use the last commit message.')
    parser.add_argument(
        '--root',
        help=
        'Custom path to directory where config directories (if any) are automatically '
        'created',
        type=nonempty_string)
    parser.add_argument(
        '--prefix',
        type=str,
        help=
        "String to preprend to all main commands, for example, sourcing a virtualenv"
    )
    parser.add_argument(
        '--dir-names',
        type=str,
        help="directories to create and sync automatically with each run")
    parser.add_argument(
        '--flags',
        type=str,
        help="directories to create and sync automatically with each run")
    parser.add_argument(
        '--assume-yes',
        '-y',
        action='store_true',
        help='Don\'t ask permission before performing operations.')
    return parser
    # new_parser.add_argument(
    #     '--summary-path',
    #     help='Path where Tensorflow summary of run is to be written.')


@UI.wrapper
@Table.wrapper
def cli(path, prefix, command, description, flags, root, dir_names, table):
    logger = table.logger
    return main(
        path=path,
        prefix=prefix,
        command=command,
        description=description,
        flags=flags,
        bash=GitBash(logger=logger),
        ui=logger,
        table=table,
        tmux=TMUXSession(path=path, bash=Bash(logger=logger)),
        file_system=FileSystem(root=root, dir_names=dir_names))


def main(path: str, prefix: str, command: str, description: str,
         flags: Optional[str], bash: GitBash, ui: UI, table: Table, tmux: TMUXSession,
         file_system: FileSystem):
    # Check if repo is dirty
    if dirty_repo():
        ui.check_permission(
            "Repo is dirty. You should commit before run. Run anyway?")

    if path in table:
        remove.execute(path=path, table=table, logger=ui,
                       file_system=file_system)

    # create directories
    for path in file_system.dir_paths(PurePath(path)):
        path.mkdir(exist_ok=True, parents=True)

    # process info
    full_command = command
    for flag in flags if flags else []:
        flag = interpolate_keywords(path, flag)
        full_command += ' ' + flag
    if prefix:
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
    table += RunEntry(path=path,
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
