import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from anytree import NodeMixin
from anytree.exporter import DictExporter

from runs.config import Config
from runs.db import no_match
from runs.run_node import RunNode
from runs.runs_path import RunsPath
from runs.tmux_session import TMUXSession
from runs.util import COMMIT, DESCRIPTION, cmd, dirty_repo, get_permission, highlight, last_commit, prune_leaves, string_from_vim, \
    prune_empty, _print, _exit


class Run:
    """
    A Run aggregates the tmux process, the directories, and the db entry relating to a run.
    """
    def __init__(self, path: str, root_node: NodeMixin, cfg: Config):
        self.path = RunsPath(path)
        self.root_node = root_node
        self.cfg = cfg
        self.tmux = None

    def node(self):
        return self.path.node(self.root_node)

    def exists(self):
        return self.node() is not None

    def keys(self):
        return [
            'command' if k is '_input_command' else k
            for k in DictExporter().export(self.node()).keys()
        ]

    # Commands
    def new(self, command, description, assume_yes, flags):
        # Check if repo is dirty
        if dirty_repo():
            prompt = "Repo is dirty. You should commit before run. Run anyway?"
            if not (assume_yes or get_permission(prompt)):
                exit()

        if self.exists():
            if assume_yes or get_permission(self.path, 'already exists. Overwrite?'):
                self.remove()
            else:
                exit()

        # create directories
        self.mkdirs()

        # process info
        for flag in flags:
            flag = self.interpolate_keywords(flag)
            command += ' ' + flag
        full_command = self.cfg.prefix + command

        # prompt = 'Edit the description of this run: (Do not edit the line or above.)'
        # if description is None:
        #     description = string_from_vim(prompt, description)
        if description is None:
            description = ''
        if description == 'commit-message':
            description = cmd('git log -1 --pretty=%B'.split())

        # tmux
        self.tmux = TMUXSession(str(self.path))
        self.tmux.new(description, full_command)

        # new db entry
        RunNode(
            name=self.path.stem,
            full_command=full_command,
            commit=last_commit(),
            datetime=datetime.now().isoformat(),
            description=description,
            _input_command=command,
            parent=self.root_node.add(self.path.parent))

        # print result
        self.print(highlight('Description:'))
        self.print(description)
        self.print(highlight('Command sent to session:'))
        self.print(full_command)
        self.print(highlight('List active:'))
        self.print('tmux list-session')
        self.print(highlight('Attach:'))
        self.print('tmux attach -t', self.tmux)

    def interpolate_keywords(self, string):
        keywords = dict(path=self.path, name=self.path.stem)
        for match in re.findall('.*<(.*)>', string):
            assert match in keywords
        for word, replacement in keywords.items():
            string = string.replace('<' + word + '>', replacement)
        return string

    def remove(self):
        if self.exists():
            self.tmux.kill()
            self.rmdirs()
            prune_leaves(self.node())
        else:
            self.exit_no_match()

    def dir_paths(self) -> List[Path]:
        return [Path(self.cfg.root, dir_name, self.path)
                for dir_name in self.cfg.dir_names]

    # file I/O
    def mkdirs(self, exist_ok: bool = True) -> None:
        for path in self.dir_paths():
            path.mkdir(exist_ok=exist_ok, parents=True)

    def rmdirs(self) -> None:
        for path in self.dir_paths():
            shutil.rmtree(str(path), ignore_errors=True)
            prune_empty(path.parent)

    def mvdirs(self, new) -> None:
        assert isinstance(new, Run)
        for old_path, new_path in zip(self.dir_paths(), new.dir_paths()):
            assert isinstance(old_path, Path)
            assert isinstance(new_path, Path)
            new_path.parent.mkdir(exist_ok=True, parents=True)
            if old_path.exists():
                old_path.rename(new_path)
                prune_empty(old_path.parent)

    def move(self, dest, kill_tmux):
        assert isinstance(dest, Run)
        self.mvdirs(dest)
        if kill_tmux:
            self.tmux.kill()
        else:
            self.tmux.rename(dest.path.stem)
        node = self.node()
        node.name = dest.head
        old_parent = node.parent
        node.parent = self.root_node.add(dest.parent)
        prune_leaves(old_parent)

    def lookup(self, key):
        if key == 'command':
            key = '_input_command'
        if key not in self.keys():
            self.exit("`{}` not a valid key. Valid keys are {}.".format(key, self.keys))
        if not self.exists():
            no_match(self.path, db_path=self.cfg.db_path)
        return getattr(self.node(), key)

    def chdescription(self, new_description):
        node = self.node()
        if new_description is None:
            new_description = string_from_vim('Edit description',
                                              node.description)
        node.description = new_description

    def reproduce(self):
        return 'To reproduce:\n' + \
               highlight('git checkout {}\n'.format(self.lookup(COMMIT))) + \
               highlight("runs new {} '{}' --description='Reproduce {}. "
                         "Original description: {}'".format(
                             self.path, self.lookup('_input_command'), self.path, self.lookup(DESCRIPTION)))

    def print(self, *msg):
        _print(*msg, quiet=self.cfg.quiet)

    def exit(self, *msg):
        _exit(*msg, quiet=self.cfg.quiet)

    def exit_already_exists(self):
        self.exit('{} already exists.'.format(self))

    def exit_no_match(self):
        no_match(self.path, self.root_node)

    def pretty_print(self):
        return """
{}
{}
Command
-------
{}
Commit
------
{}
Date/Time
---------
{}
Description
-----------
{}
""".format(self.path, '=' * len(self.path.parts),
           *map(self.lookup, ['full_command', 'commit', 'datetime', 'description']))
