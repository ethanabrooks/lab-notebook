from runs.database import Table
from runs.logger import Logger
from runs.util import highlight


@Logger.wrapper
@Table.wrapper
def main(path, table):
    print(string(path, table))


def string(path, table):
    entry = table.entry(path)
    return '\n'.join([
        'To reproduce:',
        highlight(f'git checkout {entry.commit}\n'),
        highlight(
            f"runs new {path} '{entry.input_command}' --description='Reproduce {path}. "
            f"Original description: {entry.description}'")
    ])
