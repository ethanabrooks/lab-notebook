import sqlite3
from collections import namedtuple
from copy import copy
from functools import wraps
from pathlib import Path, PurePath
from typing import List, Sequence, Union

from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.tmux_session import TMUXSession
from runs.util import PurePath

PathLike = Union[str, PurePath, PurePath, Path]

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
    dict(default='datetime', choices=RunEntry.fields(), help='Sort query by this field.')
}


def add_query_flags(
        parser,
        with_sort: bool,
        default_flags: dict = DEFAULT_QUERY_FLAGS,
):
    if not with_sort:
        default_flags = copy(default_flags)
        del default_flags['--sort']
    for arg_name, kwargs in default_flags.items():
        parser.add_argument(arg_name, **kwargs)


QueryArgs = namedtuple('QueryArgs', 'patterns unless order descendants')


class DataBase:
    @staticmethod
    def open(func):
        @wraps(func)
        def open_wrapper(db_path, quiet, *args, **kwargs):
            logger = Logger(quiet=quiet)
            with DataBase(db_path, logger) as db:
                return func(*args, **kwargs, logger=logger, db=db)

        return open_wrapper

    @staticmethod
    def bundle_query_args(func):
        @wraps(func)
        def bundle_query_args_wrapper(logger, db, patterns, descendants, unless, active,
                                      *args, **kwargs):
            if active:
                patterns = TMUXSession.active_runs(logger)
            sort = kwargs['sort'] if 'sort' in kwargs else None
            query_args = QueryArgs(
                patterns=patterns, unless=unless, order=sort, descendants=descendants)
            return func(
                *args,
                **kwargs,
                query_args=query_args,
                patterns=patterns,
                logger=logger,
                db=db)

        return bundle_query_args_wrapper

    @staticmethod
    def query(func):
        @wraps(func)
        def query_wrapper(db, query_args: QueryArgs, *args, **kwargs):
            runs = db.get(**(query_args._asdict()))
            return func(*args, **kwargs, runs=runs, db=db)

        return DataBase.bundle_query_args(query_wrapper)

    def __init__(self, path, logger: Logger):
        self.logger = logger
        self.path = path
        self.table_name = 'runs'
        self.conn = None
        self.columns = set(RunEntry.fields())
        self.key = 'path'
        self.fields = RunEntry.fields()
        self.condition = f"""
        FROM {self.table_name} WHERE {self.key} LIKE
        """

    def __enter__(self):
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

    def where(self, conditions):
        if isinstance(conditions, dict):
            keys = conditions.keys()
        else:
            keys = [self.key] * len(conditions)
        return ' WHERE ' + ' OR '.join(f'{k} LIKE ?' for k in keys)

    def select(self, arg='*', like=None, unless=None, order=None):
        string = f"""
        SELECT {arg} FROM {self.table_name}
        """
        if like:
            string += self.where(conditions=like)
        if unless:
            string += f' EXCEPT {self.select(like=unless)}'
        if order:
            if order not in self.fields:
                self.logger.exit('The following keys are invalid: '
                                 f'{", ".join(invalid_keys)}')

            string += f' ORDER BY "{order}"'
        return string

    def execute(self,
                command: str,
                patterns: Sequence[PathLike] = None,
                unless: Sequence[PathLike] = None) -> sqlite3.Cursor:
        if patterns is None:
            patterns = []
        if unless is None:
            unless = []
        values = tuple(map(str, patterns))
        if unless:
            values += tuple(map(str, unless))
        return self.conn.execute(command, values)

    def __contains__(self, *patterns: PathLike) -> bool:
        return bool(self.execute(self.select(like=patterns), patterns).fetchone())

    def get(self,
            patterns: Sequence[PathLike],
            unless: Sequence[PathLike] = None,
            order: str = None,
            descendants: bool = False) -> List[RunEntry]:
        if descendants:
            patterns = [f'{pattern}%' for pattern in patterns]
        return [
            RunEntry(PurePath(p), *e) for (p, *e) in self.execute(
                command=self.select(like=patterns, unless=unless, order=order),
                patterns=patterns,
                unless=unless,
            ).fetchall()
        ]

    def __getitem__(self, patterns: Sequence[PathLike]) -> List[RunEntry]:
        return [
            RunEntry(PurePath(p), *e)
            for (p, *e) in self.execute(self.select(like=patterns), patterns).fetchall()
        ]

    def __delitem__(self, *patterns: PathLike):
        self.execute(f'DELETE FROM {self.table_name} {self.where(patterns)}', patterns)

    def append(self, run: RunEntry):
        placeholders = ','.join('?' for _ in run)
        self.conn.execute(
            f"""
        INSERT INTO {self.table_name} ({self.fields}) VALUES ({placeholders})
        """, [str(x) for x in run])

    def all(self, unless=None, order=None):
        return [
            RunEntry(*e) for e in self.execute(
                self.select(unless=unless, order=order), unless).fetchall()
        ]

    def update(self, *patterns: PathLike, **kwargs):
        update_placeholders = ','.join([f'{k} = ?' for k in kwargs])
        self.execute(
            f"""
        UPDATE {self.table_name} SET {update_placeholders} {self.where(patterns)}
        """,
            list(kwargs.values()) + list(patterns))

    def delete(self):
        self.conn.execute(f"""
        DROP TABLE IF EXISTS {self.table_name}
        """)

    def entry(self, path: PathLike):
        entries = self[path, ]
        if len(entries) == 0:
            self.logger.exit(
                f"Found no entries for {path}. Current entries:",
                *[e.path for e in self.all()],
                sep='\n')
        if len(entries) > 1:
            self.logger.exit(f"Found multiple entries for {path}:", *entries, sep='\n')
        return entries[0]
