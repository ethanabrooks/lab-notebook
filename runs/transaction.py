from collections import namedtuple
from functools import wraps
from pathlib import Path, PurePath
from typing import List

from runs.database import DataBase
from runs.file_system import FileSystem
from runs.logger import UI
from runs.run_entry import RunEntry
from runs.shell import Bash
from runs.tmux_session import TMUXSession
from runs.util import highlight, string_from_vim

Move = namedtuple('Move', ['src', 'dest', 'kill_tmux'])
DescriptionChange = namedtuple(
    'DescriptionChange', ['path', 'full_command', 'old_description', 'new_description'])


class Transaction:
    @staticmethod
    def wrapper(func):
        @wraps(func)
        def _wrapper(db_path, root, dir_names, quiet, assume_yes, *args, **kwargs):
            transaction = Transaction(
                db_path=db_path,
                root=root,
                dir_names=dir_names,
                quiet=quiet,
                assume_yes=assume_yes)
            with transaction as open_transaction:
                return func(transaction=open_transaction, *args, **kwargs)

        return _wrapper

    def __init__(self, db_path: Path, quiet: bool, assume_yes: bool, root: Path,
                 dir_names: List[str]):
        self.ui = UI(quiet=quiet, assume_yes=assume_yes)
        self.db = DataBase(path=db_path, logger=self.ui)
        self.bash = Bash(logger=self.ui)
        self.file_system = FileSystem(root=root, dir_names=dir_names)
        self.new_runs = set()  # type: Set[RunEntry]
        self.moves = set()  # type: Set[Move]
        self.removals = set()  # type: Set[PurePath]
        self.interrupts = set()  # type: Set[PurePath]
        self.description_changes = set()  # type: Set[DescriptionChange]

    def __enter__(self):
        self.db = self.db.__enter__()
        return self

    def __exit__(self, *args):
        self.execute()
        self.db.__exit__(*args)

    def tmux(self, path):
        return TMUXSession(path=path, bash=self.bash)

    def execute_removal(self, path: PurePath):
        TMUXSession(path, bash=self.bash).kill()
        self.file_system.rmdirs(path)
        del self.db[path]

    def execute_move(self, src: PurePath, dest: PurePath, kill_tmux: bool):
        if src != dest:
            self.file_system.mvdirs(src, dest)
            tmux = TMUXSession(path=src, bash=self.bash)
            if kill_tmux:
                tmux.kill()
            else:
                tmux.rename(dest)
            self.db.update(src, path=dest)

    def create_run(self, run: RunEntry, tmux):
        for dir_path in self.file_system.dir_paths(run.path):
            dir_path.mkdir(exist_ok=True, parents=True)

        tmux.new(window_name=run.description, command=run.full_command)
        self.db.append(run)

    def validate(self):
        self.new_runs = sorted(self.new_runs)
        self.moves = sorted(self.moves)
        self.removals = sorted(self.removals)
        self.interrupts = sorted(self.interrupts)
        self.description_changes = sorted(self.description_changes)

        # description changes
        def get_description(change):
            new_description = string_from_vim(
                f"""
        Edit description for {change.path}.
        Command: {change.full_command}
        """, change.old_description)
            # noinspection PyProtectedMember
            return change._replace(new_description=new_description)

        self.description_changes = {
            c if c.new_description else get_description(c)
            for c in self.description_changes
        }

        # removals
        if self.interrupts:
            self.ui.check_permission("Sending interrupt signals to the following runs:",
                                     *self.interrupts)

        # removals
        if self.removals:
            self.ui.check_permission("Runs to be removed:", *self.removals)

        # moves
        destinations = [m.dest for m in self.moves]
        collisions = set([m for m in self.moves if destinations.count(m.dest) > 1])
        if collisions:
            self.ui.exit(
                f"Cannot move multiple runs into the same path:",
                *[f"{m.src} -> {m.dest}" for m in collisions],
                sep='\n')

        def validate_move(kill_tmux):
            moves = [m for m in self.moves if m.kill_tmux == kill_tmux]
            if moves:
                prompt = "About to perform the following moves"
                if kill_tmux:
                    prompt += "and kill the associated tmux sessions"
                self.ui.check_permission(prompt + ':',
                                         *[f"{m.src} -> {m.dest}" for m in self.moves])

        validate_move(kill_tmux=True)
        validate_move(kill_tmux=False)

        if self.new_runs and self.bash.dirty_repo():
            self.ui.check_permission(
                "Repo is dirty. You should commit before run. Run anyway?")
        if len(self.new_runs) > 1:
            self.ui.check_permission(
                "Generating the following runs:",
                *[f"{run.path}: {run.full_command}" for run in self.new_runs])

    def execute(self):
        self.validate()

        # description changes
        for change in self.description_changes:
            # noinspection PyProtectedMember
            self.db.update(change.path, description=change.new_description)

        # kills
        for path in self.interrupts:
            self.tmux(path).interrupt()

        # removals
        for path in self.removals:
            self.execute_removal(path)

        # moves
        for move in self.moves:
            self.execute_move(**move._asdict())

        # creations
        for run in self.new_runs:
            tmux = self.tmux(run.path)
            self.create_run(run=run, tmux=tmux)
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
