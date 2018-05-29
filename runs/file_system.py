import shutil
from pathlib import Path, PurePath
from typing import List

from runs.util import prune_empty


class FileSystem:
    def __init__(self, root, dir_names):
        self.root = root
        self.dir_names = dir_names

    def dir_paths(self, path: PurePath) -> List[Path]:
        return [Path(self.root, dir_name, path) for dir_name in self.dir_names]

    def mkdirs(self, path: PurePath, exist_ok: bool = True) -> None:
        for path in self.dir_paths(path):
            path.mkdir(exist_ok=exist_ok, parents=True)

    def rmdirs(self, path: PurePath) -> None:
        for path in self.dir_paths(path):
            shutil.rmtree(str(path), ignore_errors=True)
            prune_empty(path.parent)

    def mvdirs(self, old_path: PurePath, new_path: PurePath) -> None:
        for old, new in zip(
                self.dir_paths(old_path), self.dir_paths(new_path)):
            assert isinstance(old, Path)
            assert isinstance(new, Path)
            new.parent.mkdir(exist_ok=True, parents=True)
            if old.exists():
                old.rename(new)
                prune_empty(old.parent)
