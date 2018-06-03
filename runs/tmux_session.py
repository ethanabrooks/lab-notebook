from pathlib import PurePath

from runs.shell import Bash


class TMUXSession:
    def __init__(self, path: PurePath, bash: Bash):
        self.name = str(path).replace('.', ',').replace(':', ';')
        self.cmd = bash.cmd

    def new(self, window_name, command):
        self.kill()
        self.cmd('tmux new -d -s'.split() + [self.name, '-n', window_name])
        self.cmd('tmux send-keys -t'.split() + [self.name, command, 'Enter'])

    def kill(self):
        self.cmd('tmux kill-session -t'.split() + [self.name], fail_ok=True)

    def interrupt(self):
        for keys in ('^C', '^D'):
            self.cmd('tmux send-keys -t'.split() + [self.name, keys, 'Enter'])

    def rename(self, new):
        if isinstance(new, TMUXSession):
            new = str(new)
        self.cmd('tmux rename-session -t '.split() + [self.name, new], fail_ok=True)

    def __str__(self):
        return self.name
