import shutil
from contextlib import contextmanager
from pathlib import Path

import yaml
from anytree import NodeMixin, Resolver, ChildResolverError, Node
from anytree.exporter import DictExporter
from anytree.importer import DictImporter


def read(db_path):
    db_path = Path(db_path)
    if db_path.exists():
        with db_path.open() as f:
            data = yaml.load(f)
        return DictImporter().import_(data)
    return None


def write(tree, db_path):
    assert isinstance(tree, NodeMixin)
    data = DictExporter().export(tree)
    with Path(db_path).open('w') as f:
        yaml.dump(data, f, default_flow_style=False)


@contextmanager
def open_db(root, db_path):
    tree = read(db_path)
    if tree is not None:
        root = tree
    yield root
    write(root, db_path)


class DBPath:
    cfg = None
    root = Node('.')

    def __init__(self, parts, cfg=None):
        if cfg is None:
            if DBPath is None:
                raise RuntimeError('Either `cfg` has to be specified or `DBPath.cfg` has to be set')
            cfg = DBPath.cfg
        self.cfg = cfg
        self.sep = '/'
        if isinstance(parts, NodeMixin):
            self.parts = [str(node.name) for node in parts.path[1:]]
        elif isinstance(parts, str):
            self.parts = parts.split(self.sep)
        else:
            assert isinstance(parts, (list, tuple)), (parts, type(parts))
            self.parts = []
            for part in parts:
                assert isinstance(part, str)
                self.parts.extend(part.split(self.sep))
        self.path = self.sep.join(self.parts)

    @contextmanager
    def new(self):
        with open_db(DBPath.root, self.cfg.db_path) as node:
            for i, part in enumerate(self.parts):
                try:
                    node = Resolver().get(node, self.sep.join(self.parts[:i]))
                except ChildResolverError:
                    node = Node(name=part, parent=node)
            yield node

    def read(self):
        tree = read(self.cfg.db_path)
        if tree is None:
            tree = DBPath.root
        return tree

    def write(self, db):
        write(db, self.cfg.db_path)

    def node(self, root=None):
        if root is None:
            root = self.read()
        try:
            assert root is not None
            return Resolver().get(root, self.path)
        except (ChildResolverError, AssertionError):
            return None

    # DB I/O
    @contextmanager
    def open(self):
        with open_db(DBPath.root, self.cfg.db_path) as tree:
            yield self.node(tree)

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

    def mvdirs(self, new):
        for old_path, new_path in zip(self.paths, new.paths):
            old_path.rename(new_path)
