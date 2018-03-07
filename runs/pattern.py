from contextlib import contextmanager
from copy import deepcopy

from anytree import ChildResolverError
from anytree import Resolver, findall

import runs.main
from runs import db
from runs.db import DBPath, tree_string
from runs.util import get_permission, COMMIT


class Pattern(DBPath):
    # DB I/O
    @contextmanager
    def open(self):
        tree = self.read()
        yield self.runs(tree)
        self.write(tree)

    def runs(self, root=None):
        return [runs.run.Run(node) for node in self.nodes(root) if hasattr(node, COMMIT)]
        # return list(map(runs.run.Run, self.nodes(root)))

    def nodes(self, root=None):
        if root is None:
            root = self.read()
        try:
            run_nodes = [node
                         for base in Resolver().glob(root, self.path.rstrip(self.sep))
                         for node in findall(base, lambda n: hasattr(n, COMMIT))]
            assert run_nodes
            return run_nodes
        except (ChildResolverError, AssertionError):
            self.exit('No runs match pattern, "{}". Recorded runs:\n{}'.format(
                self.path, db.tree_string(db_path=self.cfg.db_path)))

    def names(self):
        return [node.name for node in self.nodes()]

    @property
    def keys(self):
        return set([key for run in self.runs() for key in run.keys])

    def remove(self, assume_yes):
        prompt = 'Runs to be removed:\n{}\nContinue?'.format('\n'.join(self.names()))
        if assume_yes or get_permission(prompt):
            for run in self.runs():
                run.remove()

    def move(self, dest, keep_tmux, assume_yes):
        assert isinstance(dest, runs.run.DBPath)

        src = self.runs()
        moves = []
        for run in src:

            # # if the dest exists or we are moving multiple runs,
            # if dest.node() is not None or len(src) > 1 or dest.is_dir:
                # preserve the current name of the run

            new_path = run.path.replace(self.path, dest.path, 1)
            dest = runs.run.Run(new_path)

            # check for conflicts with existing runs
            if dest.node() is not None:
                dest.already_exists()

            moves.append((run, dest))

        prompt = ("Planned moves:\n\n" +
                  '\n'.join(s.path + ' -> ' + d.path for s, d in moves) +
                  '\n\nContinue?')
        if assume_yes or get_permission(prompt):
            for src, dest in moves:
                src.move(dest, keep_tmux)

    def lookup(self, key):
        return [run.lookup(key) for run in self.runs()]

    def tree(self):
        tree = deepcopy(self.read())
        nodes = self.nodes(tree)

        def not_part_of_tree(node):
            return not any(node is n for n in nodes) and \
                   not any(node is a for n in nodes for a in n.ancestors)

        for node in findall(tree, not_part_of_tree):
            node.parent = None
        return tree

    def tree_string(self, print_attrs=False):
        return tree_string(tree=self.tree(), print_attrs=print_attrs)

    def table(self, column_width):
        return db.table(self.nodes(), self.cfg.hidden_columns, column_width)
