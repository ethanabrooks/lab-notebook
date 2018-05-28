import os
import re
import shutil
from datetime import datetime
from itertools import zip_longest
from pathlib import Path, PurePath
from typing import List

from runs.db import RunEntry, Table, no_match
from runs.tmux_session import TMUXSession
from runs.util import (SEP, _exit, _print, cmd, dirty_repo, get_permission,
                       highlight, last_commit, prune_empty, string_from_vim, ROOT_PATH)


class Run:
    """
    A Run aggregates the tmux process, the directories, and the db entry relating to a run.
    """

    def __init__(self, table: Table, root: os.PathLike, path: os.PathLike,
                 dir_names: str, quiet: bool):
        self.tmux = TMUXSession(str(path))
        self.root = PurePath(root)
        self.path = PurePath(path)
        self.table = table
        self.dir_names = dir_names.split()
        self.quiet = quiet

    def entry(self):
        entries = self.table[self.path]
        assert len(
            entries) == 1, f"{self.path} matches multiple runs: {entries}"
        return entries[0]

    def exists(self):
        return self.path in self.table

    def new(self, prefix, command, flags, description, assume_yes):
        # Check if repo is dirty
        if dirty_repo():
            prompt = "Repo is dirty. You should commit before run. Run anyway?"
            if not (assume_yes or get_permission(prompt)):
                exit()

        if self.exists():
            if assume_yes or get_permission(self.path,
                                            'already exists. Overwrite?'):
                self.remove()
            else:
                exit()

        # create directories
        self.mkdirs()

        # process info
        full_command = command
        for flag in flags:
            flag = self.interpolate_keywords(flag)
            full_command += ' ' + flag
        full_command = f'{prefix} {full_command}'

        # prompt = 'Edit the description of this run: (Do not edit the line or above.)'
        # if description is None:
        #     description = string_from_vim(prompt, description)
        if description is None:
            description = ''
        if description == 'commit-message':
            description = cmd('git log -1 --pretty=%B'.split())

        # tmux
        self.tmux.new(description, full_command)

        # new db entry
        self.table += RunEntry(
            path=self.path,
            full_command=full_command,
            commit=last_commit(),
            datetime=datetime.now().isoformat(),
            description=description,
            input_command=command)

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
            string = string.replace(f'<{word}>', str(replacement))
        return string

    def remove(self):
        self.tmux.kill()
        self.rmdirs()
        del self.table[self.path]

    def dir_paths(self) -> List[Path]:
        return [
            Path(self.root, dir_name, self.path) for dir_name in self.dir_names
            ]

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
        # noinspection PyProtectedMember
        self.table.update(
            self.path, **self.entry().replace(path=dest.path).asdict())

    def chdescription(self, new_description):
        if new_description is None:
            new_description = string_from_vim('Edit description',
                                              self.entry().description)
        # noinspection PyProtectedMember
        self.table.update(
            self.path, **self.entry().replace(description=new_description).asdict())

    def reproduce(self):
        entry = self.entry()
        return 'To reproduce:\n' + \
               highlight(f'git checkout {entry.commit}\n') + \
               highlight("runs new {} '{}' --description='Reproduce {}. "
                         "Original description: {}'".format(
                   self.path, entry.input_command, self.path, entry.description))

    def print(self, *msg):
        _print(*msg, quiet=self.quiet)

    def exit(self, *msg):
        _exit(*msg, quiet=self.quiet)

    def exit_already_exists(self):
        self.exit('{} already exists.'.format(self))

    def exit_no_match(self):
        no_match(self.path, self.root)

    def pretty_print(self):
        header = f'{self.path}\n{"=" * len(str(self.path))}'
        # noinspection PyProtectedMember
        entry_items = self.entry()._asdict().items()
        attributes = '\n'.join(
            [f'{k}\n{"-" * len(k)}\n{v}' for k, v in entry_items])
        return header + attributes


def move(src_pattern: str, dest_path: str, table: Table, kill_tmux: bool,
         assume_yes: bool, **kwargs):
    src_entries = table[f'{src_pattern}%']

    if dest_path in table and len(src_entries) > 1:
        _exit(
            "'{}' already exists and '{}' matches the following runs:\n{}\nCannot move multiple runs into an existing "
            "run.".format(dest_path, src_pattern, '\n'.join(map(str, src_entries))))

    def is_dir(pattern):
        return pattern == ROOT_PATH or f'{pattern.rstrip(SEP)}{SEP}%' in table

    def make_src_run(src_path) -> Run:
        return Run(path=src_path, table=table, **kwargs)

    def make_dest_run(src_path) -> Run:
        if is_dir(src_pattern):
            if is_dir(dest_path) or len(src_entries) > 1:
                old_parts = PurePath(src_pattern).parent.parts
                src_parts = PurePath(src_path).parts
                path = PurePath(dest_path,
                                *[p for p, from_old in
                                  zip_longest(src_parts, old_parts)
                                  if not from_old])
            else:
                path = PurePath(dest_path, PurePath(src_path).stem)
        else:
            if is_dir(dest_path) or len(src_entries) > 1:
                path = PurePath(dest_path, PurePath(src_path).stem)
            else:
                path = PurePath(dest_path)
        return Run(path=path, table=table, **kwargs)

    moves = {make_src_run(s.path): make_dest_run(s.path) for s in src_entries}

    # check before moving
    prompt = ("Planned moves:\n\n" + '\n'.join(f"{s.path} -> {d.path}"
                                               for s, d in moves.items()) +
              '\n\nContinue?')

    if moves and (assume_yes or get_permission(prompt)):
        # check for conflicts with existing runs
        already_exists = [str(d.path) for d in moves.values() if d.exists()]
        if already_exists:
            prompt = 'Runs to be removed:\n{}\nContinue?'.format(
                '\n'.join(already_exists))
            if not (assume_yes or get_permission(prompt)):
                _exit()

        for src_run, dest_run in moves.items():
            if src_run.path != dest_run.path:
                if dest_run.exists():
                    dest_run.remove()
                src_run.move(dest_run, kill_tmux)
