import itertools
import re
from datetime import datetime
from pathlib import PurePath
from typing import List

from runs.commands import rm
from runs.database import DataBase
from runs.file_system import FileSystem
from runs.logger import UI
from runs.run_entry import RunEntry
from runs.shell import Bash
from runs.tmux_session import TMUXSession
from runs.util import flag_list, highlight, nonempty_string_type


def add_subparser(subparsers):
    parser = subparsers.add_parser('new', help='Start a new run.')
    parser.add_argument(
        'path',
        help='Unique path assigned to new run. "\\"-delimited.',
        type=nonempty_string_type)
    parser.add_argument('command', help='Command that will be run in tmux.', type=str)
    parser.add_argument(
        '--description',
        help='Description of this run. Explain what this run was all about or '
        'just write whatever your heart desires. If this argument is `commit-message`,'
        'it will simply use the last commit message.')
    parser.add_argument(
        '--prefix',
        type=str,
        help="String to preprend to all main commands, for example, sourcing a virtualenv"
    )
    parser.add_argument(
        '--flags',
        type=flag_list,
        help="directories to create and sync automatically with each run")
    return parser
    # new_parser.add_argument(
    #     '--summary-path',
    #     help='Path where Tensorflow summary of run is to be written.')


@UI.wrapper
@DataBase.wrapper
def cli(path: PurePath, prefix: str, command: str, description: str,
        flags: List[List[str]], root: PurePath, dir_names: List[PurePath], db: DataBase,
        *args, **kwargs):
    ui = db.logger
    bash = Bash(logger=ui)
    file_system = FileSystem(root=root, dir_names=dir_names)

    runs = list(generate_runs(path, flags))
    if bash.dirty_repo():
        ui.check_permission("Repo is dirty. You should commit before run. Run anyway?")
    if len(runs) > 1:
        ui.check_permission(
            '\n'.join(["Generating the following runs:"] +
                      [f"{p}: {build_command(command, p, prefix, f)}"
                       for p, f in runs] + ["Continue?"]))

    rm.remove_with_check(
        *[path for path, _ in runs], db=db, logger=ui, file_system=file_system)

    for path, flags in runs:
        new(path=path,
            prefix=prefix,
            command=command,
            description=description,
            flags=flags,
            bash=bash,
            ui=ui,
            db=db,
            tmux=TMUXSession(path=path, bash=Bash(logger=ui)),
            file_system=file_system)


def generate_runs(path: PurePath, flags: List[List[str]]):
    flag_combinations = list(itertools.product(*flags))
    for i, flags in enumerate(flag_combinations):
        new_path = path
        if len(flag_combinations) > 1:
            new_path += str(i)
        yield new_path, flags


def build_command(command: str, path: PurePath, prefix: str, flags: List[str]) -> str:
    if prefix:
        return f'{prefix} {command}'
    flags = ' '.join(interpolate_keywords(path, f) for f in flags)
    if flags:
        command = f"{command} {flags}"
    return command


def new(path: PurePath, prefix: str, command: str, description: str,
        flags: List[str], bash: Bash, ui: UI, db: DataBase, tmux: TMUXSession,
        file_system: FileSystem):
    # create directories
    for dir_path in file_system.dir_paths(PurePath(path)):
        dir_path.mkdir(exist_ok=True, parents=True)

    full_command = build_command(command, path, prefix, flags)
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
    db.append(
        RunEntry(
            path=path,
            full_command=full_command,
            commit=bash.last_commit(),
            datetime=datetime.now().isoformat(),
            description=description,
            input_command=command))

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
    keywords = dict(path=path, name=PurePath(path).stem)
    for match in re.findall('.*<(.*)>', string):
        assert match in keywords
    for word, replacement in keywords.items():
        string = string.replace(f'<{word}>', str(replacement))
    return string
