from contextlib import contextmanager
from copy import deepcopy

from anytree import ChildResolverError
from anytree import NodeMixin
from anytree import Resolver, findall

import runs.main
from runs import db
from runs.db import tree_string
from runs.route import Route
from runs.util import get_permission, COMMIT, is_run_node


class Pattern(Route):
    # DB I/O
    @contextmanager
    def open(self):
        tree = self.read()
        yield self.runs(tree)
        self.write(tree)

    def runs(self, root=None):
        return [runs.run.Run(run)
                for base in self.nodes(root)
                for run in findall(base, is_run_node)]

    def nodes(self, root=None):
        if root is None:
            root = self.read()
        try:
            return Resolver().glob(root, self.path.rstrip(self.sep))
        except ChildResolverError:
            return []
            # self.exit('No nodes match pattern, "{}". Current tree:\n{}'.format(
            #     self.path, db.tree_string(db_path=self.cfg.db_path)))

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
        assert isinstance(dest, Route)

        dest_is_dir = dest.node() is not None or dest.is_dir

        moves = []
        nodes = self.nodes()
        for src_node in nodes:

            _dest = dest
            if dest_is_dir or len(nodes) > 1:
                # put the current node into base
                _dest = Route(dest.parts + [src_node.path[-1]])

            # check for conflicts with existing runs
            if _dest.node() is not None:
                _dest.already_exists()

            # add child runs to moves list
            for child_run_node in findall(src_node, is_run_node):
                stem = child_run_node.path[len(src_node.path):]
                dest_run = runs.run.Run(_dest.parts + list(stem))
                src_run = runs.run.Run(child_run_node)
                moves.append((src_run, dest_run))

        # check before moving
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
