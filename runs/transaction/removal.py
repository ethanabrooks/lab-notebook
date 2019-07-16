# stdlib
from pathlib import PurePath

# first party
from runs.transaction.sub_transaction import SubTransaction
from runs.util import RED, RESET


class RemovalTransaction(SubTransaction):
    def validate(self):
        self.ui.check_permission(RED, "Runs to be removed:", *self.queue, RESET)

    def process(self, path: PurePath):
        self.tmux(path).kill()
        self.file_system.rmdirs(path)
        del self.db[path]
