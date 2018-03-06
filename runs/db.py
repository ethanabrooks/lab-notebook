import shutil
from contextlib import contextmanager
from pathlib import Path

import yaml
from anytree import NodeMixin, Resolver, ChildResolverError, Node
from anytree import PreOrderIter
from anytree import RenderTree
from anytree.exporter import DictExporter
from anytree.importer import DictImporter
from tabulate import tabulate

from runs.util import NAME, _print, _exit


def read(db_path):
    db_path = Path(db_path)
    if db_path.exists():
        with db_path.open() as f:
            data = yaml.load(f)
        return DictImporter().import_(data)
    return None


def name_first(attrs):
    return [t for t in attrs if t[0] == NAME] + \
           [t for t in attrs if t[0] != NAME]


def write(tree, db_path):
    assert isinstance(tree, NodeMixin)
    data = DictExporter().export(tree)
    with Path(db_path).open('w') as f:
        yaml.dump(data, f, default_flow_style=False)


def tree_string(tree, print_attrs=False):
    assert isinstance(tree, NodeMixin)
    string = ''
    for pre, fill, node in RenderTree(tree):
        public_attrs = {k: v for k, v in vars(node).items()
                        if not k.startswith('_') and not k == 'name'}
        if public_attrs:
            pnode = yaml.dump(public_attrs, default_flow_style=False).split('\n')
        else:
            pnode = ''
        string += "{}{}\n".format(pre, node.name)
        if print_attrs:
            for line in pnode:
                string += "{}{}\n".format(fill, line)
    return string


def table(nodes, hidden_columns, column_width):
    assert isinstance(column_width, int)

    def get_values(node, key):
        try:
            value = str(getattr(node, key))
            if len(value) > column_width:
                value = value[:column_width] + '...'
            return value
        except AttributeError:
            return '_'

    keys = set([key for node in nodes for key in vars(node) if not key.startswith('_')])
    headers = sorted(set(keys) - set(hidden_columns))
    table = [[node.name] + [get_values(node, key) for key in headers]
             for node in sorted(nodes, key=lambda n: n.name)]
    return tabulate(table, headers=headers)


@contextmanager
def open_db(root, db_path):
    tree = read(db_path)
    if tree is not None:
        root = tree
    yield root
    write(root, db_path)


class DBPath:
    cfg = None
    root_path = '.'

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

        parts = self.parts
        if not parts:
            parts = self.root_path
        *self.ancestors, self.head = parts

    @property
    def parent(self):
        return DBPath(self.ancestors)

    @property
    def root(self):
        return Node(self.root_path)

    @contextmanager
    def add_to_tree(self):
        """
        Add a node corresponding to this path to the db, yield it,
        and write when finished.
        """
        if self.node():
            with self.open() as node:
                yield node
        else:
            with DBPath(self.ancestors).add_to_tree() as parent:
                yield Node(name=self.head, parent=parent)

                #
                # with open_db(self.root, self.cfg.db_path) as node:
                #     for i, part in enumerate(self.parts):
                #         try:
                #             node = Resolver().get(node, self.sep.join(self.parts[:i]))
                #         except ChildResolverError:
                #             node = Node(name=part, parent=node)
                #     yield node

    def read(self):
        tree = read(self.cfg.db_path)
        if tree is None:
            tree = self.root
        return tree

    def write(self, db):
        write(db, self.cfg.db_path)

    def node(self, root=None):
        """
         Get the node corresponding to thie path if it exists.
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
    def open(self):
        with open_db(self.root, self.cfg.db_path) as tree:
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
        assert isinstance(new, DBPath)
        for old_path, new_path in zip(self.paths, new.paths):
            new_path.parent.mkdir(exist_ok=True, parents=True)
            old_path.rename(new_path)

    def print(self, *msg):
        _print(*msg, quiet=self.cfg.quiet)

    def exit(self, *msg):
        _exit(*msg, quiet=self.cfg.quiet)
