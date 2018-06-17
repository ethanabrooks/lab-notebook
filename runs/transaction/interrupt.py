from pathlib import PurePath

from runs.transaction.sub_transaction import SubTransaction


class InterruptTransaction(SubTransaction):
    def validate(self):
        self.ui.check_permission("Sending interrupt signals to the following runs:",
                                 *self.queue)

    def process(self, path: PurePath):
        self.tmux(path).interrupt()
