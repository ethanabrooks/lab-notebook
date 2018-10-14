# stdlib
from collections.__init__ import namedtuple
import json
from pathlib import Path
from typing import List

# first party
from runs.commands.new import new
from runs.logger import UI
from runs.transaction.transaction import Transaction
from runs.util import PurePath


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'new-from-spec', help='Start a new run using a JSON specification.')

    parser.add_argument('path', type=PurePath, help='Unique path for each run. ')
    parser.add_argument(
        'spec',
        type=Path,
        help='JSON file that contains either a single or an array of JSON objects'
        'each with a "command" key and a "flags" key. The "command" value'
        'is a single string and the "flags" value is a JSON object such that'
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
        help="String to prepend to all main commands, for example, sourcing a virtualenv")
    parser.add_argument(
        '--flag',
        '-f',
        default=[],
        action='append',
        help="directories to create and sync automatically with each run")
    return parser
    # new_parser.add_argument(
    #     '--summary-path',
    #     help='Path where Tensorflow summary of run is to be written.')


Flag = namedtuple('Flag', 'key values')


class SpecObj:
    def __init__(self, command: str, flags: List[Flag], delimiter: str = '='):
        self.command = command
        self.flags = [Flag(*f) for f in flags]
        self.delimiter = delimiter


@Transaction.wrapper
def cli(prefix: str, path: PurePath, spec: Path, flags: List[str], logger: UI,
        description: str, transaction: Transaction, *args, **kwargs):
    # spec: Path
    with spec.open() as f:
        obj = json.load(f, object_pairs_hook=lambda pairs: pairs)
    try:
        try:
            array = [SpecObj(**dict(obj))]
        except TypeError:
            array = [SpecObj(**dict(o)) for o in obj]
    except TypeError:
        logger.exit(f'Each object in {spec} must have a '
                    f'"command" field and a "flags" field.')

    for i, obj in enumerate(array):
        new_path = path if len(array) == 1 else PurePath(path, str(i))

        def parse_flag(flag: Flag):
            values = flag.values if isinstance(flag.values, list) else [flag.values]
            null_keys = ['null', '', 'none', 'None']
            return [
                f'--{v}' if flag.key in null_keys else f'--{flag.key}="{v}"'
                for v in values
            ]

        flags = [[f] for f in flags]
        flags += list(map(parse_flag, obj.flags))
        new(path=new_path,
            prefix=prefix,
            command=obj.command,
            description=description,
            flags=flags,
            transaction=transaction)
