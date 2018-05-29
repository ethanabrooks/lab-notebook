from runs.database import Table
from runs.logger import Logger


@Logger.wrapper
@Table.wrapper
def cli(pattern, table):
    print(strings(pattern, table))


def strings(pattern, table):
    if pattern is None:
        pattern = '%'
    return [e.path for e in table[pattern]]
