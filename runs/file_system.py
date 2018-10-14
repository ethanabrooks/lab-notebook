# stdlib
from pathlib import Path, PurePath
import shutil
from typing import List

# first party
from runs.util import prune_empty


class FileSystem:
    def __init__(self, root: PurePath, dir_names: List[str]):
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
        for old, new in zip(self.dir_paths(old_path), self.dir_paths(new_path)):
            assert isinstance(old, Path)
            assert isinstance(new, Path)
            new.parent.mkdir(exist_ok=True, parents=True)
            if old.exists() and old.is_dir():
                try:
                    old.rename(new)
                except OSError:
                    # deal with x -> x/y
                    tmp = Path(old.parent, 'tmp')
                    old.rename(tmp)
                    new.parent.mkdir(exist_ok=True, parents=True)
                    tmp.rename(new)
                prune_empty(old.parent)
