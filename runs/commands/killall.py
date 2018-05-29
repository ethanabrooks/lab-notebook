import shutil

from runs.database import Table
from runs.logger import UI


@UI.wrapper
@Table.wrapper
def cli(ui, table, root):
    runs = [e.path for e in table.all()]
    ui.check_permission("Runs to be removed:", runs, "Continue?", sep='\n')
    table.delete()
    table.path.unlink()
    shutil.rmtree(str(root), ignore_errors=True)
