import sqlite3
from copy import copy
from functools import wraps
from pathlib import Path
from typing import Union, Iterable, List

from runs import query
from runs.logger import Logger
from runs.query import Condition, In, Like
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
        def query_wrapper(logger: Logger, db: DataBase, patterns: Iterable[str], unless: Iterable[str],
                          descendants: bool, active: bool,  order: str = None, *args, **kwargs):
            if descendants:
                patterns = [f'{pattern}/%' for pattern in patterns]
            condition = DataBase.pattern_match(*patterns)
            if active:
                condition = condition and In('path', TMUXSession.active_runs(logger))
            if unless is not None:
                unless = query.Any([Like('path', pattern) for pattern in unless])
            runs = [RunEntry(PurePath(p), *e) for (p, *e) in
                    db.select(condition=condition, unless=unless, order=order).fetchall()]
            return func(*args, **kwargs, logger=logger, runs=runs, db=db)

        return query_wrapper

    def __init__(self, path, logger: Logger):
        self.logger = logger
        self.path = path
        self.table_name = 'runs'
        self.conn = None
        self.columns = set(RunEntry.fields())
        self.key = 'path'
        self.fields = RunEntry.fields()
        # self.condition = f"""
        # FROM {self.table_name} WHERE {self.key} LIKE
        # """

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

    # def select(self, columns='*', condition: Sized = None, unless=None, order=None):
    #     string = f"""
    #     SELECT {columns} FROM {self.table_name}
    #     """
    #     if condition:
    #         string += self.where(patterns=condition)
    #     if unless:
    #         string += f' EXCEPT {self.select(condition=unless)}'
    #     if order:
    #         if order not in self.fields:
    #             self.logger.exit('The following keys are invalid: '
    #                              f'{", ".join(invalid_keys)}')
    #
    #         string += f' ORDER BY "{order}"'
    #     return string

    def check_field(self, field: str):
        if field not in self.fields + [None]:
            self.logger.exit(f'{field} must be one of the following values: {self.fields}')

    def select(self, columns: Iterable = None, condition: Condition = None, unless: Condition = None,
               order: str = None) -> sqlite3.Cursor:
        if columns is None:
            columns = ['*']
        string = f"""
        SELECT {','.join(columns)} FROM {self.table_name}
        """
        values = []
        if condition is not None:
            string += f'WHERE {condition}'
            values += condition.values()
        if unless is not None:
            string += f' EXCEPT {condition}'
            values += unless.values()
        if order is not None:
            self.check_field(order)
            string += f' ORDER BY "{order}"'
        return self.execute(string, values)

    def get(self, patterns: Iterable[PurePath], unless: Iterable[PurePath] = None, order: bool = None) -> List[RunEntry]:
        if unless is None:
            unless = []
        return [RunEntry(PurePath(p), *e) for (p, *e) in
                self.select(condition=DataBase.pattern_match(*patterns),
                            unless=DataBase.pattern_match(*unless),
                            order=order).fetchall()]

    def __getitem__(self, patterns) -> List[RunEntry]:
        if not isinstance(patterns, Iterable):
            patterns = [patterns]
        return self.get(patterns)

    def execute(self, sql: str, parameters: Iterable):
        return self.conn.execute(sql, tuple(map(str, parameters)))

    def __contains__(self, *patterns: PathLike) -> bool:
        return bool(self.select(condition=DataBase.pattern_match(*patterns)).fetchone())

    def __delitem__(self, *patterns: PathLike):
        self.execute(f'DELETE FROM {self.table_name} WHERE {DataBase.pattern_match(*patterns)}', patterns)

    def append(self, run: RunEntry):
        placeholders = ','.join('?' * len(run))
        self.execute(
            f"""
        INSERT INTO {self.table_name} ({self.fields}) VALUES ({placeholders})
        """, run)

    def all(self, unless: Condition = None, order: str = None):
        self.check_field(order)
        return [
            RunEntry(*e) for e in self.select(unless=unless, order=order).fetchall()
        ]

    def all_paths(self):
        return self.select(columns=['path'])

    def update(self, *patterns: PathLike, **kwargs):
        update_placeholders = ','.join([f'{k} = ?' for k in kwargs])
        condition = query.Any(*[Like(self.key, p) for p in patterns])
        self.conn.execute(
            f"""
        UPDATE {self.table_name} SET {update_placeholders} WHERE {condition}
        """,
            list(kwargs.values()) + condition.values())

    def delete(self):
        self.conn.execute(f"""
        DROP TABLE IF EXISTS {self.table_name}
        """)

    # def entry(self, path: PathLike):
    #     entries = self[path,]
    #     if len(entries) == 0:
    #         self.logger.exit(
    #             f"Found no entries for {path}. Current entries:",
    #             self.all_paths(),
    #             sep='\n')
    #     if len(entries) > 1:
    #         self.logger.exit(f"Found multiple entries for {path}:", *entries, sep='\n')
    #     return entries[0]
