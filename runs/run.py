import subprocess
from datetime import datetime
from pathlib import Path

from anytree import AnyNode
from anytree.exporter import DictExporter

from runs.db_path import DBPath
from runs.util import dirty_repo, get_permission, string_from_vim, last_commit, highlight, cmd


class Run(DBPath):
    def __init__(self, parts):
        super().__init__(parts)
        assert self.parts is not []
        *ancestors, self.head = self.parts
        self.parent = DBPath(ancestors)

    @property
    def keys(self):
        return list(DictExporter().export(self.node()).keys())

    # Commands
    def new(self, command, description, no_overwrite, quiet):
        # Check if repo is dirty
        if dirty_repo():
            prompt = "Repo is dirty. You should commit before run. Run anyway?"
            if not get_permission(prompt):
                exit()

        # Check if path already exists
        if self.node() is not None:
            if no_overwrite:
                print('{} already exists.'.format(self.head))
                exit()
            self.remove()

        # create directories
        self.mkdirs()

        # process info
        full_command = self.build_command(command)
        prompt = 'Edit the description of this run: (Do not edit the line or above.)'
        if description is None:
            description = string_from_vim(prompt, description)

        # tmux
        self.new_tmux(description, full_command)

        # new db entry
        with self.parent.open() as parent:
            assert parent is not None
            AnyNode(name=self.head,
                    input_command=command,
                    full_command=full_command,
                    commit=last_commit(),
                    datetime=datetime.now().isoformat(),
                    description=description,
                    parent=parent)

        # print result
        if not quiet:
            print(highlight('Description:'))
            print(description)
            print(highlight('Command sent to session:'))
            print(full_command)
            print(highlight('List active:'))
            print('tmux list-session')
            print(highlight('Attach:'))
            print('tmux attach -t', self.head)

    def build_command(self, command):
        for flag in self.cfg.flags:
            flag = flag.replace(
                '<path>', self.path).replace(
                '<root>', str(self.cfg.root)).replace(
                '<name>', self.head)
            command += ' ' + flag

        if self.cfg.virtualenv_path:
            return 'source ' + self.cfg.virtualenv_path + '/bin/activate; ' + command
        return command

    def remove(self):
        self.kill_tmux()
        self.rmdirs()
        with self.open() as node:
            node.parent = None

    def move(self, dest, keep_tmux):
        assert isinstance(dest, Run)
        self.mvdirs(dest)
        if keep_tmux:
            self.rename_tmux(dest.head)
        else:
            self.kill_tmux()
        with self.open() as node:
            node.name = dest.head
            node.parent = dest.parent

    def lookup(self, key):
        try:
            return getattr(self.node(), key)
        except AttributeError:
            raise RuntimeError(
                "`{}` not a valid key. Valid keys are {}.".format(key, self.keys))

    # tmux
    def kill_tmux(self):
        cmd('tmux kill-session -t'.split() + [self.path], fail_ok=True)

    def new_tmux(self, window_name, main_cmd):
        self.kill_tmux()
        subprocess.check_call('tmux new -d -s'.split() + [self.path, '-n', window_name])
        cd_cmd = 'cd ' + str(Path.cwd())
        for command in [cd_cmd, main_cmd]:
            cmd('tmux send-keys -t'.split() + [self.path, command, 'Enter'])

    def rename_tmux(self, new):
        cmd('tmux rename-session -t '.split() + [self.path, new], fail_ok=True)

    def chdescription(self):
        with self.open() as node:
            node.description = string_from_vim('Edit description', node.description)
