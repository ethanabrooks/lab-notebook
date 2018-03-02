from contextlib import contextmanager
from copy import deepcopy

from anytree import Resolver, findall
from tabulate import tabulate

import runs.main
from runs.db_path import DBPath
from runs.util import get_permission, highlight, COMMIT, NAME, COMMAND, DESCRIPTION, print_tree


class Pattern(DBPath):
    # DB I/O
    @contextmanager
    def open(self):
        tree = DBPath.read()
        yield self.runs(tree)
        DBPath.write(tree)

    def runs(self, root=None):
        return list(map(runs.run.Run, self.nodes(root)))

    def nodes(self, root=None):
        if root is None:
            root = DBPath.read()
        run_nodes = [node
                     for base in Resolver().glob(root, self.path)
                     for node in findall(base, lambda n: hasattr(n, '_is_run'))]
        if not run_nodes:
            print('No runs match pattern. Recorded runs:')
            print_tree(DBPath.read())
            exit()
        return run_nodes

    def names(self):
        return [node.name for node in self.nodes()]

    @property
    def keys(self):
        return set([run.keys for run in self.runs()])

    def remove(self):
        if get_permission('Remove the following runs?\n{}\n'.format(
                '\n'.join(self.names()))):
            with self.open() as runs:
                for run in runs:
                    run.remove()

    def move(self, dest, keep_tmux):
        assert isinstance(dest, runs.run.Run)

        # check for conflicts with existing runs
        if isinstance(dest, runs.run.Run):
            dest.run_exists()

        with self.runs() as src:

            # prompt depends on number of runs being moved
            if len(src) > 1:
                prompt = 'Move the following runs into {}?\n{}'.format(
                    dest.path, '\n'.join(run.path for run in src))
            else:
                prompt = 'Move {} to {}?'.format(src[0].path, dest.path)

            if get_permission(prompt):
                for run in src:

                    # if the dest exists or we are moving multiple runs,
                    if dest.node() is not None or len(src) > 1:
                        # preserve the current name of the run
                        dest = runs.run.Run(dest.path, run.head)

                    run.move(dest, keep_tmux)

    def lookup(self, key):
        return [run.lookup(key) for run in self.runs()]

    def tree(self):
        tree = deepcopy(DBPath.read())
        for node in findall(tree, lambda n: n not in self.nodes(tree)):
            node.parent = None
        return tree

    def table(self, column_width):
        def get_values(node, key):
            try:
                value = str(getattr(node, key))
                if len(value) > column_width:
                    value = value[:column_width] + '...'
                return value
            except AttributeError:
                return '_'

        headers = sorted(set(self.keys) - set(DBPath.cfg().hidden_columns))
        table = [[node.name] + [get_values(node, key) for key in headers]
                 for node in sorted(self.nodes(), key=lambda n: n.name)]
        return tabulate(table, headers=headers)

    def reproduce(self):
        if self.nodes():
            return 'To reproduce:\n' + \
                   highlight('git checkout {}\n'.format(self.lookup(COMMIT))) + \
                   highlight("runs new {} '{}' --no-overwrite --description='{}'".format(
                       self.lookup(NAME), self.lookup(COMMAND), self.lookup(DESCRIPTION)))
