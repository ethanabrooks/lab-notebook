import json
from pathlib import Path
from typing import List, Tuple, Any

from runs.commands.new import new, Flag
from runs.logger import UI
from runs.transaction.transaction import Transaction
from runs.util import PurePath


def flags_hook(pairs: List[Tuple[Any, Any]]):
    keys, values = zip(*pairs)
    if len(set(keys)) != len(keys):  # duplicates
        return [Flag(key=k, values=v if isinstance(v, (list, tuple)) else [v]) for k, v in pairs]
    return dict(pairs)


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'new-from-spec',
        help='Start a new run using a JSON specification.')

    parser.add_argument(
        'path',
        type=PurePath,
        help='Unique path for each run. '
    )
    parser.add_argument(
        'spec',
        type=Path,
        help='JSON file that contains either a single or an array of JSON objects'
             'each with a "command" key and a "flags" key. The "command" value'
             'is a single string and the "flags" value is a JSON object such that'
             '"a: b," becomes "--a=b" for example.',
    )
    parser.add_argument(
        '--description',
        dest='descriptions',
        help='Description of this run. Explain what this run was all about or '
             'write whatever your heart desires. If this argument is `commit-message`,'
             'it will simply use the last commit message.')
    parser.add_argument(
        '--prefix',
        type=str,
        help="String to prepend to all main commands, for example, sourcing a virtualenv"
    )
    return parser
    # new_parser.add_argument(
    #     '--summary-path',
    #     help='Path where Tensorflow summary of run is to be written.')


class SpecObj:
    def __init__(self, command: str, flags: List[Flag], delimiter: str = '='):
        self.command = command
        self.flags = flags
        self.delimiter = delimiter


@Transaction.wrapper
def cli(prefix: str, path: PurePath, spec: Path,
        logger: UI, description: str, transaction: Transaction,
        *args, **kwargs):
    # spec: Path
    with spec.open() as f:
        array = json.load(f, object_pairs_hook=flags_hook)
    if isinstance(array, dict):
        array = [array]

    for i, obj in enumerate(array):
        try:
            obj = SpecObj(**obj)
        except TypeError:
            logger.exit(f'Each object in {spec.path} must have a '
                        f'"command" field and a "flags" field.')
        new_path = path if len(array) == 1 else PurePath(path, str(i))
        new(path=new_path,
            prefix=prefix,
            command=obj.command,
            description=description,
            flags=obj.flags,
            transaction=transaction)
