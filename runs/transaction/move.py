# stdlib
from collections import namedtuple

# first party
from runs.transaction.sub_transaction import SubTransaction
from runs.util import highlight

Move = namedtuple('Move', ['src', 'dest', 'kill_tmux'])


class MoveTransaction(SubTransaction):
    def add(self, move):
        assert isinstance(move, Move)
        self.queue.add(move)

    def validate(self):
        destinations = [m.dest for m in self.queue]
        collisions = set([m for m in self.queue if destinations.count(m.dest) > 1])
        if collisions:
            self.ui.exit(
                f"Cannot move multiple runs into the same path:",
                *[f"{m.src} -> {m.dest}" for m in collisions],
                sep='\n')

        def validate_move(kill_tmux):
            moves = [m for m in self.queue if m.kill_tmux == kill_tmux]
            if moves:
                prompt = highlight("About to perform the following moves")
                if kill_tmux:
                    prompt += highlight(" and kill the associated tmux sessions")
                self.ui.check_permission(prompt + ':',
                                         *[f"{m.src} -> {m.dest}" for m in self.queue])

        validate_move(kill_tmux=True)
        validate_move(kill_tmux=False)

    def process(self, move: Move):
        if move.src != move.dest:
            self.file_system.mvdirs(move.src, move.dest)
            tmux = self.tmux(move.src)
            if move.kill_tmux:
                tmux.kill()
            else:
                tmux.rename(move.dest)
            self.db.update(move.src, path=move.dest)
