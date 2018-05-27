from runs.util import cmd


class TMUXSession:
    def __init__(self, name: str):
        self.name = name.replace('.', ',').replace(':', ';')

    def new(self, window_name, command):
        self.kill()
        cmd('tmux new -d -s'.split() + [self.name, '-n', window_name])
        cmd('tmux send-keys -t'.split() + [self.name, command, 'Enter'])

    def kill(self):
        cmd('tmux kill-session -t'.split() + [self.name], fail_ok=True)

    def rename(self, new):
        if isinstance(new, str):
            new = TMUXSession(new)
        assert isinstance(new, TMUXSession)
        cmd('tmux rename-session -t '.split() + [self.name, new], fail_ok=True)

    def __str__(self):
        return self.name

