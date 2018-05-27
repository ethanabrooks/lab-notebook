import shutil
from contextlib import contextmanager
from pathlib import Path, PurePath
from typing import Optional

from anytree import ChildResolverError, Node, NodeMixin, Resolver

from runs.cfg import Cfg
from runs.db import open_db
from runs.util import ROOT_PATH, SEP, _exit, _print, prune_empty


class RunsPath(Path):
    config = None

    @property
    def cfg(self) -> Cfg:
        if RunsPath.cfg is None:
            raise RuntimeError('RunsPath.cfg is not set.')
        return RunsPath.config

    def node(self, root: NodeMixin) -> Optional[NodeMixin]:
        """
         Get the node corresponding to this path if it exists.
        Otherwise return None.
         """
        try:
            return Resolver().get(root, self.is_absolute())
        except ChildResolverError:
            return None

    def nodes(self, root):
        try:
            # if self.path is '.':
            #     return list(PreOrderIter(root))
            return Resolver().glob(root, str(self).rstrip(SEP))
        except ChildResolverError:
            return []

    def glob(self, pattern):
        with self.cfg.root.open() as f:
            root =
        return [
            SEP.join([n.name for n in node.path])
            for node in self.nodes()
            ]
        pass

    def rglob(self, pattern):
        pass

    def open(self, mode='r', *args):
        with self.root.open(mode) as root:
            yield self.node(root)

    def dir_paths(self):
        return [
            Path(self.cfg.root, dir_name, self.path)
            for dir_name in self.cfg.dir_names
            ]

    # file I/O
    def mkdirs(self, exist_ok=True):
        for path in self.dir_paths:
            path.mkdir(exist_ok=exist_ok, parents=True)

    def rmdirs(self):
        for path in self.paths:
            shutil.rmtree(str(path), ignore_errors=True)
            prune_empty(path.parent)

    def mvdirs(self, new):
        assert isinstance(new, DBPath)
        for old_path, new_path in zip(self.paths, new.paths):
            new_path.parent.mkdir(exist_ok=True, parents=True)

            # TODO: what to do if old_path has a different name to
            # to changes in the .runsrc
            if old_path.exists():
                old_path.rename(new_path)
                prune_empty(old_path.parent)

    def print(self, *msg):
        _print(*msg, quiet=self.cfg.quiet)

    def exit(self, *msg):
        _exit(*msg, quiet=self.cfg.quiet)

    def exit_already_exists(self):
        self.exit('{} already exists.'.format(self))

    def __str__(self):
        return self.path
