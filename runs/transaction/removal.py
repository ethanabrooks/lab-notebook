# stdlib
from pathlib import PurePath

# first party
from runs.transaction.sub_transaction import SubTransaction


class RemovalTransaction(SubTransaction):
    def validate(self):
        self.ui.check_permission("Runs to be removed:", *self.queue)

    def process(self, path: PurePath):
        self.tmux(path).kill()
        self.file_system.rmdirs(path)
        del self.db[path]
