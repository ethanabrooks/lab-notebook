import itertools
import json
from pathlib import Path
from typing import List, Dict

from runs.commands.new import new_run, Flag, run_args
from runs.logger import UI
from runs.transaction.transaction import Transaction
from runs.util import PurePath


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        'new-from-spec',
        help='Start a new run using a JSON specification.')

    parser.add_argument(
        '--path',
        nargs='+',
        dest='paths',
        action='append',
        type=PurePath,
        help='Unique path for each run. '
             'Number of paths and number of command-specs must be equal.',
        metavar='PATH'
    )
    parser.add_argument(
        '--spec',
        nargs='+',
        dest='specs',
        action='append',
        type=Path,
        help='JSON file that contains either a single or an array of JSON objects'
             'each with a "command" key and a "flags" key. The "command" value'
             'is a single string and the "flags" value is a JSON object such that'
             '"a: b," becomes "--a=b" for example.',
    )
    parser.add_argument(
        '--description',
        dest='descriptions',
        action='append',
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
def cli(prefix: str, paths: List[PurePath], specs: List[Path],
        logger: UI, descriptions: List[str], transaction: Transaction,
        *args, **kwargs):
    # spec: Path
    for path, spec, description in zip(paths, specs, descriptions):
        with spec.open() as f:
            obj = json.load(f)
        if isinstance(obj, dict):
            obj = [obj]
        try:
            obj_list = [SpecObj(**k) for k in obj]
        except TypeError:
            logger.exit(f'Each object in {spec.path} must have a '
                        f'"command" field and a "flags" field.')

        # arg: RunArg
        commands, flags = zip(obj_list)
        for arg in run_args(paths=paths,
                            commands=commands,
                            descriptions=descriptions,
                            flags=flags):
            new_run(**args._asdict(),
                    prefix=prefix,
                    transaction=transaction)
