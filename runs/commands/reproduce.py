# stdlib
from collections import defaultdict
import json
from typing import List, Optional

# first party
from runs.database import DataBase, add_query_flags
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import PurePath, highlight, interpolate_keywords


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'reproduce',
        help='Print commands to reproduce a run or runs. This command '
        'does not have side-effects (besides printing).')
    add_query_flags(parser, with_sort=False)
    parser.add_argument(
        '--path',
        type=PurePath,
        default=None,
        help="This is for cases when you want to run the reproduced command on a new path."
    )
    parser.add_argument(
        '--description',
        type=str,
        default=None,
        help="Description to be assigned to new run. If None, use the same description as "
        "the run being reproduced.")
    return parser


@DataBase.open
@DataBase.query
def cli(runs: List[RunEntry], flags: List[str], logger: Logger, db: DataBase, prefix: str,
        path: Optional[PurePath], description: str, *args, **kwargs):
    for string in strings(
            db=db,
            runs=runs,
            flags=flags,
            prefix=prefix,
            path=path,
            description=description,
    ):
        logger.print(string)


def strings(runs: List[RunEntry], flags: List[str], prefix: str, db: DataBase,
            path: Optional[PurePath], description: Optional[str]):
    entry_dict = defaultdict(list)
    return_strings = [highlight('To reproduce:')]
    for entry in runs:
        entry_dict[entry.commit].append(entry)
    for commit, entries in entry_dict.items():
        return_strings.append(f'git checkout {commit}')
        command_string = 'runs new'
        for i, entry in enumerate(entries):
            if path is None:
                new_path = entry.path
            elif len(entries) > 1:
                new_path = PurePath(path, str(i))
            else:
                new_path = path

            subcommand = get_command_string(
                path=PurePath(new_path),
                prefix=prefix,
                command=entry.command,
                flags=flags)
            new_path, subcommand, _description = map(json.dumps, [
                str(new_path), subcommand, description
                or entry.description.strip('"').strip("'")
            ])
            join_string = ' ' if len(entries) == 1 else ' \\\n'
            command_string = join_string.join([
                command_string,
                f'--path={new_path}',
                f'--command={subcommand}',
                f'--description={_description}',
            ])
        return_strings.append(command_string)
    return return_strings


def get_command_string(path: PurePath, prefix: str, command: str,
                       flags: List[str]) -> str:
    flags = [interpolate_keywords(path, f) for f in flags]
    for s in flags + [prefix]:
        command = command.replace(s, '')
    return command
    # command_string = f"runs new {new_path} '{command}' --description='Reproduce {entry.path}. "
    # f"Original description: {entry.description}'"
    # return command_string
