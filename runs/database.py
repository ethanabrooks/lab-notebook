import sqlite3
from functools import wraps
from pathlib import Path, PurePath
from typing import List, Sequence, Union

from runs.logger import Logger
from runs.run_entry import RunEntry

PathLike = Union[str, PurePath, Path]


class DataBase:
    @staticmethod
    def wrapper(func):
        @wraps(func)
        def db_wrapper(db_path, logger, *args, **kwargs):
            with DataBase(db_path, logger) as db:
                return func(*args, **kwargs, db=db)

        return db_wrapper

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

    def select(self, arg='*', like=None, unless=None):
        string = f"""
        SELECT {arg} FROM {self.table_name}
        """
        if like:
            string += self.where(conditions=like)
        if unless:
            string += f' EXCEPT {self.select(like=unless)}'
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

    def get(self, patterns: Sequence[PathLike], unless=None) -> List[RunEntry]:
        return [
            RunEntry(*e) for e in self.execute(
                self.select(like=patterns, unless=unless), patterns).fetchall()
        ]

    def __getitem__(self, patterns: Sequence[PathLike]) -> List[RunEntry]:
        return [
            RunEntry(PurePath(p), *e)
            for p, *e in self.execute(self.select(like=patterns), patterns).fetchall()
        ]

    def descendants(self, *patterns: PathLike, unless=None):
        patterns = [f'{pattern}%' for pattern in patterns]
        return self.get(patterns, unless=unless)

    def __delitem__(self, *patterns: PathLike):
        self.execute(f'DELETE FROM {self.table_name} {self.where(patterns)}', patterns)

    def append(self, run: RunEntry):
        placeholders = ','.join('?' for _ in run)
        self.conn.execute(
            f"""
        INSERT INTO {self.table_name} ({self.fields}) VALUES ({placeholders})
        """, [str(x) for x in run])

    def all(self, unless=None):
        return [
            RunEntry(*e)
            for e in self.execute(self.select(unless=unless), unless).fetchall()
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
