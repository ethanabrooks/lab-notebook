from runs.util import cmd


class TMUXSession:
    def __init__(self, name: str):
        self.name = name.replace('.', ',').replace(':', ';')

    def new(self):
        cmd('tmux kill-session -t'.split() + [self.name], fail_ok=True)

    def kill(self):
        cmd('tmux kill-session -t'.split() + [self.name], fail_ok=True)

    def rename(self, new):
        if isinstance(new, str):
            new = TMUXSession(new)
        assert isinstance(new, TMUXSession)
        cmd('tmux rename-session -t '.split() + [self.name, new], fail_ok=True)


