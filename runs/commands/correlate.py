import math
import re
from pathlib import Path, PurePath
from typing import Callable, Dict, List, Optional

from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry


def add_subparser(subparsers):
    parser = subparsers.add_parser('correlate', help='Rank flags by correlation.')
    parser.add_argument(
        'patterns',
        nargs='*',
        help='Analyze the flags associated with these runs',
        type=PurePath)
    parser.add_argument(
        'path_to_value',
        type=Path,
        help='The command will look for a file at this path containing'
        'a scalar value. It will assess the correlation between flags and this value.'
        'The keyword <path> will be replaced by the path of the run.')
    parser.add_argument(
        '--unless',
        nargs='*',
        type=PurePath,
        help='Exclude these paths from the analysis.')
    return parser


@Logger.wrapper
@DataBase.wrapper
def cli(patterns: List[PurePath], db: DataBase, unless: List[PurePath],
        path_to_value: Path, *args, **kwargs):
    db.logger.print(
        *strings(
            'correlation, flag',
            *patterns,
            db=db,
            unless=unless,
            path_to_value=path_to_value),
        sep='\n')


def strings(*args, **kwargs):
    cor = correlations(*args, **kwargs)
    keys = sorted(cor.keys(), key=lambda k: cor[k])
    return [f'{cor[k]}, {k}' for k in keys]


def get_flags(command: str) -> List[str]:
    findall = re.findall('(?:[A-Z]*=\S* )*\S* (\S*)', command)
    return findall


def correlations(*patterns,
                 db: DataBase,
                 path_to_value: Path,
                 unless: List[PurePath] = None) -> Dict[str, float]:
    runs = db.get(patterns, unless=unless)

    def mean(f: Callable) -> float:
        return sum(map(f, runs)) / float(len(runs))

    def get_value(path: PurePath) -> Optional[float]:
        try:
            with Path(str(path_to_value).replace('<path>', str(path))).open() as f:
                return float(f.read())
        except (ValueError, FileNotFoundError):
            return

    runs = [r for r in runs if get_value(r.path) is not None]
    if not runs:
        return {}
    value_mean = mean(lambda run: get_value(run.path))
    value_std_dev = math.sqrt(mean(lambda run: (get_value(run.path) - value_mean)**2))

    def get_correlation(flag: str) -> float:
        def contains_flag(run: RunEntry) -> float:
            return float(flag in get_flags(run.full_command))

        flag_mean = mean(contains_flag)

        covariance = mean(
            lambda run: (contains_flag(run) - flag_mean) * (get_value(run.path) - value_mean)
        )

        std_dev = math.sqrt(mean(lambda run: (contains_flag(run) - flag_mean)**2))

        # return covariance
        denominator = std_dev * value_std_dev
        if denominator:
            return covariance / denominator
        else:
            return math.inf

    flags = {flag for run in runs for flag in get_flags(run.full_command)}
    return {
        flag: get_correlation(flag)
        for flag in flags if get_correlation(flag) < math.inf
    }
