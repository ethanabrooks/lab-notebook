import shutil
from contextlib import contextmanager
from pathlib import Path

from anytree import NodeMixin, Node, Resolver, ChildResolverError

from runs.db import read, write, open_db
from runs.util import prune_empty, _print, _exit, SEP, ROOT_PATH


class Route:
    cfg = None

    def __init__(self, parts, cfg=None):
        if cfg is None:
            if Route is None:
                raise RuntimeError('Either `cfg` has to be specified or `DBPath.cfg` has to be set')
            cfg = Route.cfg
        self.cfg = cfg
        self.sep = SEP
        self.root_path = ROOT_PATH
        if isinstance(parts, NodeMixin):
            self.parts = [str(node.name) for node in parts.path[1:]]
        elif isinstance(parts, str):
            self.parts = parts.split(self.sep)
        else:
            assert isinstance(parts, (list, tuple)), (parts, type(parts))
            for part in parts:
                assert isinstance(part, (str, NodeMixin))
            strings = [p for p in parts if isinstance(p, str)]
            nodes = [p for p in parts if isinstance(p, NodeMixin)]
            self.parts = [s for string in strings
                          for s in string.split(self.sep)] + \
                         [n.name for n in nodes]
        assert isinstance(self.parts, list)
        self.is_dir = not self.parts or self.parts[-1] == ''
        self.parts = [p for p in self.parts if p]
        if not self.parts:
            self.parts = [self.root_path]
        self.path = self.sep.join(self.parts)
        *self.ancestors, self.head = self.parts

    @property
    def parent(self):
        return Route(self.ancestors)

    @property
    def root(self):
        return Node(self.root_path)

    def add_to_tree(self, root=None):
        """
        Add a node corresponding to this path to root (or to the db if root is None)
        """
        node = self.node(root)
        if node:
            return node
        parent = self.parent.add_to_tree(root)
        return Node(name=self.head, parent=parent)

    def read(self):
        tree = read(self.cfg.db_path)
        if tree is None:
            tree = self.root
        return tree

    def write(self, db):
        write(db, self.cfg.db_path)

    def node(self, root=None):
        """
         Get the node corresponding to this path if it exists.
        Otherwise return None.
         """
        if root is None:
            root = self.read()
        try:
            assert root is not None
            return Resolver().get(root, self.path)
        except (ChildResolverError, AssertionError):
            return None

    # DB I/O
    @contextmanager
    def open_root(self):
        with open_db(self.root, self.cfg.db_path) as root:
            yield root

    @contextmanager
    def open(self):
        with self.open_root() as root:
            yield self.node(root)

    @property
    def paths(self):
        return [Path(self.cfg.root, dir_name, self.path)
                for dir_name in self.cfg.dir_names]

    # file I/O
    def mkdirs(self, exist_ok=True):
        for path in self.paths:
            path.mkdir(exist_ok=exist_ok, parents=True)

    def rmdirs(self):
        for path in self.paths:
            shutil.rmtree(str(path), ignore_errors=True)
            prune_empty(path.parent)

    def mvdirs(self, new):
        assert isinstance(new, Route)
        for old_path, new_path in zip(self.paths, new.paths):
            new_path.parent.mkdir(exist_ok=True, parents=True)
            old_path.rename(new_path)
            prune_empty(old_path.parent)

    def print(self, *msg):
        _print(*msg, quiet=self.cfg.quiet)

    def exit(self, *msg):
        _exit(*msg, quiet=self.cfg.quiet)

    def already_exists(self):
        self.exit('{} already exists.'.format(self))

    def __str__(self):
        return self.path