# stdlib
from pathlib import PurePath

# first party
from runs.transaction.sub_transaction import SubTransaction


class KillTransaction(SubTransaction):
    def validate(self):
        self.ui.check_permission("Kill TMUX sessions for the following runs:",
                                 *self.queue)

    def process(self, path: PurePath):
        self.tmux(path).kill()
