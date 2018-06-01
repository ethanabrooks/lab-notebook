import codecs
import re
from datetime import datetime
from pathlib import PurePath

import itertools

from runs.commands import rm
from runs.database import RunEntry, DataBase
from runs.file_system import FileSystem
from runs.logger import UI
from runs.shell import Bash
from runs.tmux_session import TMUXSession
from runs.util import PATH, highlight, nonempty_string


def add_subparser(subparsers):
    parser = subparsers.add_parser('new', help='Start a new run.')
    parser.add_argument(
        PATH,
        help='Unique path assigned to new run. "\\"-delimited.',
        type=nonempty_string)
    parser.add_argument(
        'command', help='Command that will be run in tmux.', type=nonempty_string)
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
        type=str,
        help="directories to create and sync automatically with each run")
    return parser
    # new_parser.add_argument(
    #     '--summary-path',
    #     help='Path where Tensorflow summary of run is to be written.')


@UI.wrapper
@DataBase.wrapper
def cli(path: str, prefix: str, command: str, description: str, flags: str,
        root: str, dir_names: str, db: DataBase, *args, **kwargs):
    ui = db.logger
    bash = Bash(logger=ui)
    file_system = FileSystem(root=root, dir_names=dir_names)

    if flags:
        flags = codecs.decode(flags, encoding='unicode_escape').strip('\n').split('\n')
    else:
        flags = []
    flag_variants = []
    for flag in flags:
        if re.match('--[^=]*=.*', flag):
            key, values = flag.split('=')
            flag_variants.append([key + '=' + value for value in values.split('|')])
        elif re.match('--[^=]* .*', flag):
            key, values = flag.split(' ')
            flag_variants.append([key + ' ' + value for value in values.split('|')])
        else:
            flag_variants.append([flag])

    runs = list(generate_runs(path, flag_variants))
    if len(runs) > 1:
        ui.check_permission('\n'.join(["Generating the following runs:"] +
                                      [f"{p}: {build_command(command, p, prefix, f)}"
                                       for p, f in runs] +
                                      ["Continue?"]))

    if bash.dirty_repo():
        ui.check_permission("Repo is dirty. You should commit before run. Run anyway?")
    for path, flags in runs:
        # Check if repo is dirty
        if path in db:
            rm.remove(path=path, db=db, logger=ui, file_system=file_system)

    for path, flags in runs:
        new(
            path=path,
            prefix=prefix,
            command=command,
            description=description,
            flags=flags,
            bash=bash,
            ui=ui,
            db=db,
            tmux=TMUXSession(path=path, bash=Bash(logger=ui)),
            file_system=file_system)


def generate_runs(path: str, flags):
    flag_combinations = list(itertools.product(*flags))
    for i, flags in enumerate(flag_combinations):
        new_path = path
        if len(flag_combinations) > 1:
            new_path += str(i)
        yield new_path, flags


def build_command(command, path, prefix, flags):
    for flag in flags:
        flag = interpolate_keywords(path, flag)
        command += ' ' + flag
    if prefix:
        return f'{prefix} {full_command}'
    return command


def new(path: str, prefix: str, command: str, description: str, flags: list, bash: Bash,
        ui: UI, db: DataBase, tmux: TMUXSession, file_system: FileSystem):
    # create directories
    for dir_path in file_system.dir_paths(PurePath(path)):
        dir_path.mkdir(exist_ok=True, parents=True)

    # process info
    full_command = command
    for flag in flags:
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
    db.append(RunEntry(
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
