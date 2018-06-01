import sqlite3
from collections import namedtuple
from functools import wraps
from pathlib import Path, PurePath
from typing import List, Tuple, Union

from runs.logger import Logger


# noinspection PyClassHasNoInit
class RunEntry(
    namedtuple('RunEntry', [
        'path', 'full_command', 'commit', 'datetime', 'description', 'input_command'
    ])):
    __slots__ = ()

    class KeyError(KeyError):
        pass

    def __str__(self):
        # noinspection PyUnresolvedReferences
        return ','.join([f"'{x}'" for x in self])

    def replace(self, **kwargs):
        return super()._replace(**kwargs)

    @staticmethod
    def fields() -> Tuple[str]:
        return RunEntry(*RunEntry._fields)

    def asdict(self) -> dict:
        return self._asdict()

    def get(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise RunEntry.KeyError


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

    # noinspection PyMethodMayBeStatic
    def condition(self) -> str:
        return f"""
        FROM {self.table_name} WHERE {self.key} LIKE ?
        """

    def __contains__(self, pattern: PathLike) -> bool:
        return bool(
            self.conn.execute(f"""
            SELECT COUNT(*) {self.condition()}
            """, (str(pattern),)).fetchone()[0])

    def __getitem__(self, pattern: PathLike) -> List[RunEntry]:
        return [
            RunEntry(*e) for e in self.conn.execute(f"""
        SELECT * {self.condition()}
        """, (str(pattern),)).fetchall()
            ]

    def __delitem__(self, pattern: PathLike):
        self.conn.execute(f"""
        DELETE {self.condition()}
        """, (str(pattern),))

    def append(self, run: RunEntry):
        self.conn.execute(f"""
        INSERT INTO {self.table_name} ({self.fields})
        VALUES ({','.join('?' for _ in run)})
        """, tuple(str(x) for x in run))

    def all(self):
        return [
            RunEntry(*e) for e in self.conn.execute(f"""
            SELECT * FROM {self.table_name}
            """).fetchall()
            ]

    def update(self, pattern: PathLike, **kwargs):
        updates = ','.join(f"'{k}' = '{v}'" for k, v in kwargs.items())
        self.conn.execute(f"""
        UPDATE {self.table_name} SET {updates} WHERE {self.key} LIKE ?
        """, (str(pattern),))

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


def tree_string(tree, print_attrs=True):
    string = ''
    # TODO
    # for pre, fill, node in RenderTree(tree):
    #     public_attrs = {
    #         k: v
    #         for k, v in vars(node).items()
    #         if not k.startswith('_') and not k == 'name'
    #     }
    #     if public_attrs:
    #         pass
    #         # pnode = yaml.dump(
    #         #     public_attrs, default_flow_style=False).split('\n')
    #     else:
    #         pnode = ''
    #     string += "{}{}\n".format(pre, node.name)
    #     if print_attrs:
    #         for line in pnode:
    #             string += "{}{}\n".format(fill, line)
    return string
