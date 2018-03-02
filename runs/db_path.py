import shutil
from contextlib import contextmanager
from pathlib import Path

import yaml
from anytree import NodeMixin, Resolver, ChildResolverError
from anytree.exporter import DictExporter
from anytree.importer import DictImporter


class DBPath:
    cfg = None

    def __init__(self, parts, cfg=None):
        if cfg is None:
            if DBPath is None:
                raise RuntimeError('Either `cfg` has to be specified or `DBPath.cfg` has to be set')
            cfg = DBPath.cfg
        self.cfg = cfg
        self.sep = '/'
        if isinstance(parts, NodeMixin):
            self.parts = [str(node.name) for node in parts.path]
        elif isinstance(parts, str):
            self.parts = parts.split(self.sep)
        else:
            assert isinstance(parts, (list, tuple)), (parts, type(parts))
            self.parts = []
            for part in parts:
                assert isinstance(part, str)
                self.parts.extend(part.split(self.sep))
        self.path = self.sep.join(self.parts)

    def read(self):
        node = None
        db_path = Path(self.cfg.db_path)
        if db_path.exists():
            with db_path.open() as f:
                data = yaml.load(f)
            node = DictImporter().import_(data)
        return node

    def write(self, db):
        if db is None:
            data = dict()
        else:
            data = DictExporter().export(db)
        with Path(self.cfg.db_path).open('w') as f:
            yaml.dump(data, f, default_flow_style=False)


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
        root = self.read()
        yield self.node(root)
        self.write(root)

    @property
    def Paths(self):
        return [Path(self.cfg.root_dir, dir_name, self.path)
                for dir_name in self.cfg.dir_names]

    # file I/O
    def mkdirs(self, exist_ok=True):
        for path in self.Paths:
            path.mkdir(exist_ok=exist_ok)

    def rmdirs(self):
        for path in self.Paths:
            shutil.rmtree(str(path))

    def mvdirs(self, new):
        for old_path, new_path in zip(self.Paths, new.Paths):
            old_path.rename(new_path)
