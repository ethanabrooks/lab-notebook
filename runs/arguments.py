from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import PurePath
import re

from runs.run_entry import RunEntry


def parse_time_delta(string: str):
    match = re.match(r"(?:(\d+)weeks?)?(?:(\d+)days?)?(?:(\d+)hours?)?", string)
    week, day, hour = [int(n) if n else 0 for n in match.group(1, 2, 3)]
    return timedelta(weeks=week, days=day, hours=hour)


def parse_datetime(string: str):
    return datetime.strptime(string, '%y-%m-%d')


DEFAULT_QUERY_FLAGS = {
    'patterns':
    dict(nargs='*', type=PurePath, help='Look up runs matching these patterns'),
    '--unless':
    dict(nargs='*', type=PurePath, help='Exclude these paths from the search.'),
    '--active':
    dict(action='store_true', help='Include all active runs in query.'),
    '--descendants':
    dict(action='store_true', help='Include all descendants of pattern.'),
    '--sort':
    dict(default='datetime', choices=RunEntry.fields(), help='Sort query by this field.'),
    '--since':
    dict(
        default=None,
        type=parse_datetime,
        help='Only display runs since this date (use isoformat).'),
    '--from-last':
    dict(
        default=None,
        type=parse_time_delta,
        help='Only display runs created in the given time delta. '
        'Either use "months", "weeks", "days", "hours" to specify time, e.g.'
        '"2weeks1day" or specify a date: month/day/year.')
}


def add_query_args(
        parser,
        with_sort: bool,
        default_args: dict = DEFAULT_QUERY_FLAGS,
):
    if not with_sort:
        default_args = deepcopy(default_args)
        del default_args['--sort']
    for arg_name, kwargs in default_args.items():
        parser.add_argument(arg_name, **kwargs)
