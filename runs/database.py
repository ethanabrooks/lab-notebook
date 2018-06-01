import sqlite3
from functools import wraps
from pathlib import Path, PurePath
from typing import List, Tuple, Union

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

    def execute(self, command: str, patterns: Tuple[PathLike]) -> sqlite3.Cursor:
        condition = ' OR '.join([f'{self.key} LIKE ?'] * len(patterns))
        values = tuple(map(str, patterns))
        return self.conn.execute(
            f"""
                {command} WHERE {condition}
                """, values)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

    def __contains__(self, *patterns: PathLike) -> bool:
        return bool(
            self.execute(f"""
        SELECT COUNT (*) FROM {self.table_name}
        """, patterns).fetchone()[0])

    def __getitem__(self, *patterns: PathLike) -> List[RunEntry]:
        return [
            RunEntry(*e) for e in self.execute(
                f"""
        SELECT * FROM {self.table_name}
        """, patterns).fetchall()
        ]

    def descendants(self, *patterns: PathLike):
        patterns = [f'{pattern}%' for pattern in patterns]
        return self.__getitem__(*patterns)

    def __delitem__(self, *patterns: PathLike):
        self.execute(f'DELETE FROM {self.table_name}', patterns)

    def append(self, run: RunEntry):
        placeholders = ','.join('?' for _ in run)
        self.conn.execute(
            f"""
        INSERT INTO {self.table_name} ({self.fields}) VALUES ({placeholders})
        """, [str(x) for x in run])

    def all(self):
        return [
            RunEntry(*e) for e in self.conn.execute(f"""
            SELECT * FROM {self.table_name}
            """).fetchall()
        ]

    def update(self, *patterns: PathLike, **kwargs):
        update_placeholders = ','.join([f'{k} = ?' for k in kwargs])
        pattern_placeholders = ','.join(['?'] * len(patterns))
        self.conn.execute(
            f"""
        UPDATE {self.table_name} SET {update_placeholders}
        WHERE {self.key} LIKE {pattern_placeholders}
        """,
            tuple(
                # updates:
                [str(v) for v in kwargs.values()] +
                # patterns:
                [str(p) for p in patterns]))

    def delete(self):
        self.conn.execute(f"""
        DROP TABLE IF EXISTS {self.table_name}
        """)

    def entry(self, path: PathLike):
        entries = self[path]
        if len(entries) == 0:
            self.logger.exit(
                f"Found no entries for {path}. Current entries:",
                *[e.path for e in self.all()],
                sep='\n')
        if len(entries) > 1:
            self.logger.exit(f"Found multiple entries for {path}:", *entries, sep='\n')
        return entries[0]
