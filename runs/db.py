import pickle
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import yaml
from anytree import NodeMixin, RenderTree, Node
from anytree.exporter import DictExporter
from anytree.importer import DictImporter
from tabulate import tabulate

from runs.util import NAME, ROOT_PATH, _exit, get_permission


class DataBase:
    def __init__(self, path: Path):
        assert isinstance(path, Path)
        self.path = path

    def read(self) -> Optional[NodeMixin]:
        with self.path.open('rb') as f:
            return DictImporter().import_(pickle.load(f))

    def write(self, tree) -> None:
        assert isinstance(tree, NodeMixin)
        data = DictExporter().export(tree)
        with self.path.open('wb') as f:
            pickle.dump(data, f)


def tree_string(tree: NodeMixin, print_attrs=True):
    string = ''
    for pre, fill, node in RenderTree(tree):
        public_attrs = {
            k: v
            for k, v in vars(node).items()
            if not k.startswith('_') and not k == 'name'
        }
        if public_attrs:
            pnode = yaml.dump(
                public_attrs, default_flow_style=False).split('\n')
        else:
            pnode = ''
        string += "{}{}\n".format(pre, node.name)
        if print_attrs:
            for line in pnode:
                string += "{}{}\n".format(fill, line)
    return string


def table(runs, hidden_columns, column_width):
    assert isinstance(column_width, int)

    def get_values(run, key):
        try:
            value = str(getattr(run.node(), key))
            if len(value) > column_width:
                value = value[:column_width] + '...'
            return value
        except AttributeError:
            return '_'

    keys = set([
        key for run in runs for key in vars(run.node())
        if not key.startswith('_')
    ])
    headers = sorted(set(keys) - set(hidden_columns))
    table = [[run.path] + [get_values(run, key) for key in headers]
             for run in sorted(runs, key=lambda r: r.path)]
    return tabulate(table, headers=headers)


def killall(db_path, root):
    if db_path.exists():
        if get_permission("Curent runs:\n{}\nDestroy all?".format(
                tree_string(db_path=db_path))):
            db_path.unlink()
    shutil.rmtree(root, ignore_errors=True)


def no_match(pattern, tree=None, db_path=None):
    _exit('No runs match pattern "{}". Recorded runs:\n{}'.format(
        pattern, tree_string(tree, db_path)))


@contextmanager
def open_db(root, db_path):
    tree = read(db_path)
    if tree is not None:
        root = tree
    yield root
    write(root, db_path)
