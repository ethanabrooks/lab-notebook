# stdlib
import itertools
import json
from pathlib import Path
from typing import List

# first party
from runs.logger import UI
from runs.subcommands.new import new
from runs.transaction.transaction import Transaction
from runs.command import Command
from runs.util import PurePath


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'new-from-spec', help='Start a new run using a JSON specification.')

    parser.add_argument('path', type=PurePath, help='Unique path for each run. ')
    parser.add_argument(
        'spec',
        type=Path,
        help='JSON file that contains either a single or an array of JSON objects'
        'each with a "command" key and a "args" key. The "command" value'
        'is a single string and the "args" value is a JSON object such that'
        '"a: b," becomes "--a=b" for example.',
    )
    parser.add_argument(
        'description',
        help='Description of this run. Explain what this run was all about or '
        'write whatever your heart desires. If this argument is `commit-message`,'
        'it will simply use the last commit message.')
    parser.add_argument(
        '--prefix',
        type=str,
        help="String to prepend to all main subcommands, for example, sourcing a "
        "virtualenv")
    parser.add_argument(
        '--arg',
        '-f',
        default=[],
        action='append',
        help="directories to create and sync automatically with each run")
    return parser
    # new_parser.add_argument(
    #     '--summary-path',
    #     help='Path where Tensorflow summary of run is to be written.')


class SpecObj:
    def __init__(self, command: str, args: dict, delimiter: str = '='):
        self.command = command
        self.args = args
        self.delimiter = delimiter

    def dict(self):
        return dict(command=self.command, args=self.args)


ARG_KWD = '<arg>'


@Transaction.wrapper
def cli(prefix: str, path: PurePath, spec: Path, args: List[str], logger: UI,
        description: str, transaction: Transaction, *_, **__):
    # spec: Path
    with spec.open() as f:
        obj = json.load(f, object_pairs_hook=lambda pairs: pairs)
    try:
        try:
            spec_objs = [SpecObj(**dict(obj))]
        except TypeError:
            spec_objs = [SpecObj(**dict(o)) for o in obj]
    except TypeError:
        logger.exit(f'Each object in {spec} must have a '
                    f'"command" field and a "args" field.')

    def process_arg(key, value, delim='='):
        if key == '':
            if value == '':
                return ''
            return process_arg(key=value, value='', delim='')
        if not key.startswith('-'):
            key = f'--{key}'
        return f'{key}{delim}"{value}"'

    def process_args(k, v):
        if isinstance(v, (list, tuple)):
            for value in v:
                yield process_arg(k, value)
        else:
            yield process_arg(k, v)

    def arg_assignments():
        for spec in spec_objs:
            for arg_set in itertools.product(*[process_args(*f) for f in spec.args]):
                yield spec.command, arg_set

    assignments = list(arg_assignments())
    for i, (command, arg_set) in enumerate(assignments):
        new_path = path if len(assignments) == 1 else PurePath(path, str(i))
        new(path=new_path,
            command=Command(prefix, command, *arg_set, *args, path=new_path),
            description=description,
            transaction=transaction)
