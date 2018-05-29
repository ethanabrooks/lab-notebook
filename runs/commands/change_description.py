from runs.database import Table
from runs.logger import Logger
from runs.util import string_from_vim


@Logger.wrapper
@Table.wrapper
def cli(path, new_description, table):
    entry = table.entry(path)
    if new_description is None:
        new_description = string_from_vim('Edit description',
                                          entry.description)
    table.update(path, description=new_description)
