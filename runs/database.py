import sqlite3
from functools import wraps
from pathlib import Path, PurePath
from typing import List, Union, Tuple, NamedTuple

from runs.logger import Logger
from runs.run_entry import RunEntry

PathLike = Union[str, PurePath, Path]


class Substitutions(NamedTuple):
    placeholders: str
    values: Tuple[str]

    @staticmethod
    def get(patterns: tuple):
        return Substitutions(placeholders=','.join('?' for _ in patterns),
                             values=tuple(map(str, patterns)))


class Conn:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, command, values=None):
        print(command)
        if values:
            print(values)
            return self.conn.execute(command, values)
        else:
            return self.conn.execute(command)
        print()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


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
        self.conn = Conn(sqlite3.connect(str(self.path)))
        # noinspection PyUnresolvedReferences
        fields = [f"'{f}' text NOT NULL" for f in self.fields]
        fields[0] += ' PRIMARY KEY'
        self.conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} ({', '.join(fields)})
        """)
        return self

    def execute(self, command: str, patterns: Tuple[PathLike]) -> sqlite3.Cursor:
        placeholders = ','.join('?' for _ in patterns)
        values = tuple(map(str, patterns))
        return self.conn.execute(f"""
        {command} WHERE {self.key} LIKE {placeholders}
        """, values)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

    def __contains__(self, *patterns: PathLike) -> bool:
        return bool(self.execute(f"""
        SELECT COUNT (*) FROM {self.table_name}
        """, patterns).fetchone()[0])

    def __getitem__(self, *patterns: PathLike) -> List[RunEntry]:
        return [RunEntry(*e) for e in self.execute(f"""
        SELECT * FROM {self.table_name}
        """, patterns).fetchall()]

    def __delitem__(self, *patterns: PathLike):
        self.execute(f'DELETE FROM {self.table_name}', patterns)

    def append(self, run: RunEntry):
        placeholders = ','.join('?' for _ in run)
        self.conn.execute(f"""
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
        self.conn.execute(f"""
        UPDATE {self.table_name} SET {update_placeholders}
        WHERE {self.key} LIKE {pattern_placeholders}
        """, tuple(
            # updates:
            [str(v) for v in kwargs.values()] +
            # patterns:
            [str(p) for p in patterns]
        ))

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
