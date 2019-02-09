# stdlib
from collections import defaultdict
import json
from typing import List, Optional

# first party
from runs.arguments import add_query_args
from runs.command import Command
from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import PurePath, highlight, interpolate_keywords, get_args


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'reproduce',
        help='Print subcommands to reproduce a run or runs. This command '
        'does not have side-effects (besides printing).')
    add_query_args(parser, with_sort=False)
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
    parser.add_argument(
        '--prefix',
        type=str,
        help="String that would be prepended to commands, and should therefore be "
        "excluded from the reproduce command ")
    return parser


@DataBase.open
@DataBase.query
def cli(runs: List[RunEntry], args: List[str], logger: Logger, db: DataBase, prefix: str,
        path: Optional[PurePath], description: str, *_, **__):
    for string in strings(
            db=db,
            runs=runs,
            args=args,
            prefix=prefix,
            path=path,
            description=description,
    ):
        logger.print(string)


def strings(runs: List[RunEntry], args: List[str], prefix: str, db: DataBase,
            description: Optional[str], path: Optional[PurePath]):
    entry_dict = defaultdict(list)
    return_strings = [highlight('To reproduce:')]
    for entry in runs:
        entry_dict[entry.commit].append(entry)
    for commit, entries in entry_dict.items():
        return_strings.append(f'git checkout {commit}')
        string = 'runs new'
        for i, entry in enumerate(entries):
            if path is None:
                new_path = entry.path
            elif len(entries) > 1:
                new_path = PurePath(path, str(i))
            else:
                new_path = path

            command = Command(*entry.command.split(), path=entry.path)
            command_args = [
                f'{k}="{v}"' if k else v for k, v in get_args(command, exclude=set(args))
            ]
            command = Command(*command.stem, *command_args, path=entry.path)
            command = str(command).lstrip(prefix)
            new_path, command, _description = map(json.dumps, [
                str(new_path), command, description
                or entry.description.strip('"').strip("'")
            ])
            join_string = ' ' if len(entries) == 1 else ' \\\n'
            string = join_string.join([
                string,
                f'--path={new_path}',
                f'--command={command}',
                f'--description={_description}',
            ])
        return_strings.append(string)
    return return_strings
