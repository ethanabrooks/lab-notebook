from runs.database import Table
from runs.logger import Logger
from runs.util import highlight, REPRODUCE, PATH, nonempty_string


@Logger.wrapper
@Table.wrapper
def cli(path, table, *args, **kwargs):
    print(string(path, table))


def string(path, table):
    entry = table.entry(path)
    return '\n'.join([
        'To reproduce:',
        highlight(f'git checkout {entry.commit}\n'),
        highlight(
            f"runs new {path} '{entry.input_command}' --description='Reproduce {path}. "
            f"Original description: {entry.description}'")
    ])


def add_reproduce_parser(subparsers):
    reproduce_parser = subparsers.add_parser(
        REPRODUCE,
        help='Print commands to reproduce a run. This command '
             'does not have side-effects (besides printing).')
    reproduce_parser.add_argument(PATH)
    reproduce_parser.add_argument(
        '--description',
        type=nonempty_string,
        default=None,
        help=
        "Description to be assigned to new run. If None, use the same description as "
        "the run being reproduced.")
    reproduce_parser.add_argument(
        '--no-overwrite',
        action='store_true',
        help='If this flag is given, a timestamp will be '
             'appended to any new name that is already in '
             'the database.  Otherwise this entry will '
             'overwrite any entry with the same name. ')
    return reproduce_parser