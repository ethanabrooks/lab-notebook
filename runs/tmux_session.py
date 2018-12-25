# stdlib
from pathlib import PurePath

# first party
from runs.shell import Bash


class TMUXSession:
    replacements = {'.': '<,>', ':': '<;>'}

    def __init__(self, bash: Bash, path: PurePath = None):
        self.name = str(path)
        for k, v in TMUXSession.replacements.items():
            self.name = self.name.replace(k, v)
        self.cmd = bash.cmd

    def new(self, window_name, command):
        self.cmd('tmux new -d -s'.split() + [self.name, '-n', window_name])
        self.cmd('tmux send-keys -t'.split() + [self.name, command, 'Enter'])

    def kill(self):
        self.cmd('tmux kill-session -t'.split() + [self.name], fail_ok=True)

    def rename(self, new):
        if isinstance(new, TMUXSession):
            new = str(new)
        self.cmd('tmux rename-session -t '.split() + [self.name, new], fail_ok=True)

    def __str__(self):
        return self.name

    @staticmethod
    def list(logger):
        bash = Bash(logger)
        return bash.cmd("tmux list-session -F #{session_name}".split()).split('\n')

    @staticmethod
    def active_runs(logger):
        paths = TMUXSession.list(logger)
        for path in paths:
            for k, v in TMUXSession.replacements.items():
                path = path.replace(v, k)
            yield path
