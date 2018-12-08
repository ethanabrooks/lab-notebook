# stdlib
from collections import namedtuple
from copy import deepcopy
from datetime import datetime, timedelta, date
from functools import wraps
from pathlib import Path
import sqlite3
from typing import Iterable, List, Union

# first party
from runs import query
from runs.logger import Logger
from runs.query import Condition, In, Like, GreaterThan
from runs.run_entry import RunEntry
from runs.tmux_session import TMUXSession
from runs.util import PurePath
import re

PathLike = Union[str, PurePath, PurePath, Path]


def parse_datetime(string: str):
    return datetime.strptime(string, '%y-%m-%d')


def parse_time_delta(string: str):
    match = re.match(r"(?:(\d+)weeks?)?(?:(\d+)days?)?(?:(\d+)hours?)?", string)
    week, day, hour = [int(n) if n else 0 for n in match.group(1, 2, 3)]
    return timedelta(weeks=week, days=day, hours=hour)


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


def add_query_flags(
        parser,
        with_sort: bool,
        default_flags: dict = DEFAULT_QUERY_FLAGS,
):
    if not with_sort:
        default_flags = deepcopy(default_flags)
        del default_flags['--sort']
    for arg_name, kwargs in default_flags.items():
        parser.add_argument(arg_name, **kwargs)


QueryArgs = namedtuple('QueryArgs', 'patterns unless order descendants active')


class DataBase:
    def pattern_match(*patterns: str):
        return query.Any(*[Like('path', pattern) for pattern in patterns])

    @staticmethod
    def open(func):
        @wraps(func)
        def open_wrapper(db_path, quiet, *args, **kwargs):
            logger = Logger(quiet=quiet)
            with DataBase(db_path, logger) as db:
                return func(*args, **kwargs, logger=logger, db=db)

        return open_wrapper

    @staticmethod
    def query(func):
        @wraps(func)
        def query_wrapper(logger: Logger,
                          db: DataBase,
                          patterns: Iterable[PurePath],
                          unless: Iterable[PurePath],
                          descendants: bool,
                          active: bool,
                          since: datetime,
                          from_last: timedelta,
                          order: str = None,
                          *args,
                          **kwargs):
            query_args = QueryArgs(
                patterns=patterns,
                unless=unless,
                order=order,
                descendants=descendants,
                active=active)
            runs = db.get(
                patterns=patterns,
                unless=unless,
                order=order,
                descendants=descendants,
                active=active,
                since=since,
                from_last=from_last,
            )
            return func(
                *args, **kwargs, logger=logger, runs=runs, db=db, query_args=query_args)

        return query_wrapper

    def __init__(self, path, logger: Logger):
        self.logger = logger
        self.path = path
        self.table_name = 'runs'
        self.conn = None
        self.columns = set(RunEntry.fields())
        self.key = 'path'
        self.fields = RunEntry.fields()

    def __enter__(self):
        if not self.path.parent.exists():
            self.logger.exit(
                f'parent directory of database does not exist: {self.path.parent}')
        self.conn = sqlite3.connect(str(self.path))
        # noinspection PyUnresolvedReferences
        fields = [f"'{f}' text NOT NULL" for f in self.fields]
        fields[0] += ' PRIMARY KEY'
        self.conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} ({', '.join(fields)})
        """)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

    def check_field(self, field: str):
        if field not in list(self.fields) + [None]:
            self.logger.exit(
                f'{field} must be one of the following values: {self.fields}')

    def select(self,
               columns: Iterable[str] = None,
               condition: Condition = None,
               unless: Condition = None,
               order: str = None) -> sqlite3.Cursor:
        if columns is None:
            columns = ['*']
        select = f"""
        SELECT {','.join(columns)} FROM {self.table_name}
        """
        sql = select
        values = []

        def check():
            assert sql.count('?') == len(values)

        if condition:
            sql += f'WHERE {condition}'
            values += condition.values()
            check()
        if unless:
            sql += f' EXCEPT {select} WHERE {unless}'
            values += unless.values()
            check()
        if order:
            self.check_field(order)
            sql += f' ORDER BY "{order}"'
        check()
        return self.execute(sql, values)

    def get(
            self,
            patterns: Iterable[PurePath],
            unless: Iterable[PurePath] = None,
            order: bool = None,
            descendants: bool = False,
            active: bool = False,
            since: datetime = None,
            from_last: timedelta = None,
    ) -> List[RunEntry]:

        if descendants:
            patterns = list(map(str, patterns))
            patterns += [f'{str(pattern).rstrip("/%")}/%' for pattern in patterns]
        condition = DataBase.pattern_match(*patterns)
        if since or from_last:
            if since:
                time = since
            if from_last:
                time = datetime.now() - from_last
            if since and from_last:
                time = max(datetime.now() - from_last, since)
            condition = condition & GreaterThan('datetime', time)
        if active:
            condition = condition & In('path', *TMUXSession.active_runs(self.logger))
        if unless:
            unless = DataBase.pattern_match(*unless)

        return [
            RunEntry(PurePath(p), *e) for (p, *e) in self.select(
                condition=condition, unless=unless, order=order).fetchall()
        ]

    def __getitem__(self, patterns) -> List[RunEntry]:
        if not isinstance(patterns, Iterable):
            patterns = [patterns]
        return self.get(patterns)

    def execute(self, sql: str, parameters: Iterable):
        return self.conn.execute(sql, tuple(map(str, parameters)))

    def __contains__(self, *patterns: PathLike) -> bool:
        return bool(self.select(condition=DataBase.pattern_match(*patterns)).fetchone())

    def __delitem__(self, *patterns: PathLike):
        self.execute(
            f'DELETE FROM {self.table_name} WHERE {DataBase.pattern_match(*patterns)}',
            patterns)

    def append(self, run: RunEntry):
        placeholders = ','.join('?' * len(run))
        self.execute(
            f"""
        INSERT INTO {self.table_name} ({self.fields}) VALUES ({placeholders})
        """, run)

    def all(self, unless: Condition = None, order: str = None):
        self.check_field(order)
        return [RunEntry(*e) for e in self.select(unless=unless, order=order).fetchall()]

    def all_paths(self):
        return self.select(columns=['path'])

    def update(self, *patterns: PathLike, **kwargs):
        update_placeholders = ','.join([f'{k} = ?' for k in kwargs])
        condition = query.Any(*[Like(self.key, p) for p in patterns])
        self.execute(
            f"""
        UPDATE {self.table_name} SET {update_placeholders} WHERE {condition}
        """,
            list(kwargs.values()) + condition.values())

    def delete(self):
        self.conn.execute(f"""
        DROP TABLE IF EXISTS {self.table_name}
        """)
