from collections import namedtuple

from runs.run_entry import RunEntry
from runs.transaction.sub_transaction import SubTransaction
from runs.util import highlight

Move = namedtuple('Move', ['src', 'dest', 'kill_tmux'])


class NewRunTransaction(SubTransaction):
    def add(self, new_run):
        assert isinstance(new_run, RunEntry)
        self.queue.add(new_run)

    def validate(self):
        if self.queue and self.bash.dirty_repo():
            self.ui.check_permission(
                "Repo is dirty. You should commit before run. Run anyway?")
        if len(self.queue) > 1:
            self.ui.check_permission(
                "Generating the following runs:",
                *[f"{run.path}: {run.full_command}" for run in self.queue])

    def process(self, run: RunEntry):
        tmux = self.tmux(run.path)
        for dir_path in self.file_system.dir_paths(run.path):
            dir_path.mkdir(exist_ok=True, parents=True)

        tmux.new(window_name=run.description, command=run.full_command)
        self.db.append(run)
        self.ui.print(
            highlight('Description:'),
            run.description,
            highlight('Command sent to session:'),
            run.full_command,
            highlight('List active:'),
            'tmux list-session',
            highlight('Attach:'),
            f'tmux attach -t {tmux}',
            '',
            sep='\n')
