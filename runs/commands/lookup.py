from runs.database import RunEntry, Table
from runs.logger import Logger


@Logger.wrapper
@Table.wrapper
def main(path, key, table):
    print(string(table, path, key, table.logger))


def string(table, path, key, logger):
    try:
        return table.entry(path)
    except AttributeError:
        logger.exit(
            f"{key} is not a valid key. Valid keys are:",
            RunEntry.fields(),
            sep='\n')
