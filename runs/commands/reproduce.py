import re
import shlex
from collections import defaultdict
from typing import List, Optional

from runs.database import DataBase
from runs.logger import Logger
from runs.util import RunPath, highlight, interpolate_keywords


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'reproduce',
        help='Print commands to reproduce a run. This command '
        'does not have side-effects (besides printing).')
    parser.add_argument('patterns', nargs='+', type=RunPath)
    parser.add_argument(
        '--path',
        type=RunPath,
        default=None,
        help="This is for cases when you want to run the reproduced command on a new path."
    )
    parser.add_argument(
        '--description',
        type=str,
        default=None,
        help="Description to be assigned to new run. If None, use the same description as "
        "the run being reproduced.")
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Without this flag, runs paths either get a number appended to them or '
        'have an existing number incremented. With this flag, the reproduced run '
        'just gets overwritten.')
    parser.add_argument(
        '--unless',
        nargs='*',
        type=RunPath,
        help='Print list of path names without tree '
        'formatting.')
    return parser


@Logger.wrapper
@DataBase.wrapper
def cli(patterns: List[RunPath], unless: List[RunPath], db: DataBase, flags: List[str],
        prefix: str, overwrite: bool, path: Optional[RunPath], *args, **kwargs):
    for string in strings(
            *patterns,
            unless=unless,
            db=db,
            flags=flags,
            prefix=prefix,
            overwrite=overwrite,
            path=path):
        db.logger.print(string)


def strings(*patterns, unless: List[RunPath], db: DataBase, flags: List[str], prefix: str,
            overwrite: bool, path: Optional[RunPath]):
    entry_dict = defaultdict(list)
    return_strings = [highlight('To reproduce:')]
    for entry in db.descendants(*patterns, unless=unless):
        entry_dict[entry.commit].append(entry)
    for commit, entries in entry_dict.items():
        return_strings.append(f'git checkout {commit}')
        command_string = 'runs new'
        for i, entry in enumerate(entries):
            new_path = get_path_string(
                path=path or entry.path,
                i=i if len(entries) > 1 else None,
                db=db,
                overwrite=overwrite)
            subcommand = get_command_string(
                path=RunPath(new_path), prefix=prefix, command=entry.command, flags=flags)
            new_path, subcommand, description = map(
                shlex.quote, [new_path, subcommand, entry.description])
            if len(entries) == 1:
                command_string += f" {new_path} {subcommand} --description={description}"
            else:
                command_string += ' \\\n  '.join([
                    f'--path={new_path}',
                    f'--command={subcommand}',
                    f'--description={description}',
                    '',
                ])
        return_strings.append(command_string)
    return return_strings


def get_path_string(path: RunPath, i: Optional[int], db: DataBase,
                    overwrite: bool) -> str:
    path = str(path)
    if i:
        path += str(i)
    if overwrite:
        return path
    while path in db:
        pattern = re.compile('(.*\.)(\d*)')
        match = pattern.match(str(path))
        if match:
            _, stem, number = match
            path = stem + str(number)
        else:
            path += '.1'
    return path


def get_command_string(path: RunPath, prefix: str, command: str, flags: List[str]) -> str:
    flags = [interpolate_keywords(path, f) for f in flags]
    for s in flags + [prefix]:
        command = command.replace(s, '')
    return command
    # command_string = f"runs new {new_path} '{command}' --description='Reproduce {entry.path}. "
    # f"Original description: {entry.description}'"
    # return command_string
