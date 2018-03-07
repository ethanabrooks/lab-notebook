import re
import subprocess
from datetime import datetime
from pathlib import Path

from anytree import AnyNode
from anytree.exporter import DictExporter

import runs.route
from runs.util import dirty_repo, get_permission, string_from_vim, last_commit, highlight, cmd, COMMIT, DESCRIPTION, \
    NAME, prune_leaves


class Run(runs.route.Route):
    @property
    def keys(self):
        return list(DictExporter().export(self.node()).keys())

    # Commands
    def new(self, command, description, assume_yes):
        # Check if repo is dirty
        if dirty_repo():
            prompt = "Repo is dirty. You should commit before run. Run anyway?"
            if not (assume_yes or get_permission(prompt)):
                exit()

        # Check if path already exists
        if self.node() is not None:
            if assume_yes or get_permission(self.path, 'already exists. Overwrite?'):
                self.remove()
            else:
                exit()

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
        with self.open_root() as root:
            AnyNode(name=self.head,
                    full_command=full_command,
                    commit=last_commit(),
                    datetime=datetime.now().isoformat(),
                    description=description,
                    _input_command=command,
                    parent=self.parent.add_to_tree(root))

        # print result
        self.print(highlight('Description:'))
        self.print(description)
        self.print(highlight('Command sent to session:'))
        self.print(full_command)
        self.print(highlight('List active:'))
        self.print('tmux list-session')
        self.print(highlight('Attach:'))
        self.print('tmux attach -t', self.path)

    def build_command(self, command):
        keywords = dict(
            path=self.path,
            name=self.head
        )
        for flag in self.cfg.flags:
            for match in re.findall('.*<(.*)>', flag):
                assert match in keywords
            for word, replacement in keywords.items():
                flag = flag.replace('<' + word + '>', replacement)
            command += ' ' + flag

        if self.cfg.virtualenv_path:
            return 'source ' + self.cfg.virtualenv_path + '/bin/activate; ' + command
        return command

    def remove(self):
        self.kill_tmux()
        self.rmdirs()
        with self.open() as node:
            if node:
                prune_leaves(node)

    def move(self, dest, keep_tmux):
        assert isinstance(dest, Run)
        self.mvdirs(dest)
        if keep_tmux:
            self.rename_tmux(dest.head)
        else:
            self.kill_tmux()
        with self.open_root() as root:
            node = self.node(root)
            node.name = dest.head
            old_parent = node.parent
            node.parent = dest.parent.add_to_tree(root)
            prune_leaves(old_parent)

    def lookup(self, key):
        try:
            return getattr(self.node(), key)
        except AttributeError:
            self.exit(
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

    def chdescription(self, new_description):
        with self.open() as node:
            if new_description is None:
                new_description = string_from_vim('Edit description', node.description)
            node.description = new_description

    def reproduce(self, no_overwrite):
        path = self.path
        if no_overwrite:
            path += datetime.now().isoformat()
        return 'To reproduce:\n' + \
               highlight('git checkout {}\n'.format(self.lookup(COMMIT))) + \
               highlight("runs new {} '{}' --description='Reproduce {}. "
                         "Original description: {}'".format(
                   path, self.lookup('_input_command'), self.path, self.lookup(DESCRIPTION)))
