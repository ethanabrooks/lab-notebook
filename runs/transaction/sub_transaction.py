# stdlib
import abc
from pathlib import PurePath

# first party
from runs.database import DataBase
from runs.file_system import FileSystem
from runs.logger import UI
from runs.shell import Bash
from runs.tmux_session import TMUXSession


class SubTransaction:
    def __init__(self, db: DataBase, bash: Bash, ui: UI, file_system: FileSystem):
        self.db = db
        self.ui = ui
        self.file_system = file_system
        self.bash = bash
        self.tmux = lambda path: TMUXSession(path=path, bash=bash)
        self.queue = set()

    def add(self, path):
        assert isinstance(path, PurePath), type(path)
        self.queue.add(path)

    @abc.abstractmethod
    def validate(self):
        pass

    @abc.abstractmethod
    def process(self, queue_element):
        pass
