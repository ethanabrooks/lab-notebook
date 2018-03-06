from contextlib import contextmanager
from copy import deepcopy

import yaml
from anytree import ChildResolverError
from anytree import RenderTree
from anytree import Resolver, findall
from tabulate import tabulate

import runs.main
from runs import db
from runs.db import DBPath, tree_string
from runs.util import get_permission, highlight, COMMIT, NAME, COMMAND, DESCRIPTION


class Pattern(DBPath):
    # DB I/O
    @contextmanager
    def open(self):
        tree = self.read()
        yield self.runs(tree)
        self.write(tree)

    def runs(self, root=None):
        return list(map(runs.run.Run, self.nodes(root)))

    def nodes(self, root=None):
        if root is None:
            root = self.read()
        try:
            run_nodes = [node
                         for base in Resolver().glob(root, self.path)
                         for node in findall(base, lambda n: hasattr(n, COMMIT))]
            assert run_nodes
            return run_nodes
        except (ChildResolverError, AssertionError):
            self.quit('No runs match pattern, {}. Recorded runs:'.format(self.path))

    def names(self):
        return [node.name for node in self.nodes()]

    @property
    def keys(self):
        return set([key for run in self.runs() for key in run.keys])

    def remove(self, assume_yes):
        prompt = 'Remove the following runs?\n{}\n'.format('\n'.join(self.names()))
        if assume_yes or get_permission(prompt):
            for run in self.runs():
                run.remove()

    def move(self, dest, keep_tmux, assume_yes):
        assert isinstance(dest, runs.run.Run)

        # check for conflicts with existing runs
        if dest.node() is not None:
            dest.already_exists()

        src = self.runs()

        # prompt depends on number of runs being moved
        if len(src) > 1:
            prompt = 'Move the following runs into {}?\n{}'.format(
                dest.parent, '\n'.join(run.parent for run in src))
        else:
            prompt = 'Move {} to {}?'.format(src[0].parent, dest.parent)

        if assume_yes or get_permission(prompt):
            for run in src:

                # if the dest exists or we are moving multiple runs,
                if dest.node() is not None or len(src) > 1:
                    # preserve the current name of the run
                    dest = runs.run.Run(dest.parent, run.head)

                run.move(dest, keep_tmux)

    def lookup(self, key):
        return [run.lookup(key) for run in self.runs()]

    def tree(self):
        tree = deepcopy(self.read())
        for node in findall(tree, lambda n: n not in self.nodes(tree)):
            node.parent = None
        return tree

    def tree_string(self, print_attrs=False):
        return tree_string(self.tree(), print_attrs)

    def table(self, column_width):
        return db.table(self.nodes(), self.cfg.hidden_columns, column_width)

    def reproduce(self):
        if self.nodes():
            return 'To reproduce:\n' + \
                   highlight('git checkout {}\n'.format(self.lookup(COMMIT))) + \
                   highlight("runs new {} '{}' --no-overwrite --description='{}'".format(
                       self.lookup(NAME), self.lookup(COMMAND), self.lookup(DESCRIPTION)))
