from contextlib import contextmanager
from copy import deepcopy
from itertools import zip_longest

from anytree import ChildResolverError
from anytree import NodeMixin
from anytree import Resolver, findall

import runs.main
from runs import db
from runs.db import tree_string
from runs.route import Route
from runs.util import get_permission, COMMIT


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
                for run in findall(base, lambda n: hasattr(n, COMMIT))]

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

    def move(self, dest_route, keep_tmux, assume_yes):
        assert isinstance(dest_route, Route)

        dest_is_dir = dest_route.node() is not None or dest_route.is_dir
        dest_parts = dest_route.parts

        def get_parts(node):
            assert isinstance(node, NodeMixin)
            return [n.name for n in node.path]

        moves = []
        for src_node in self.nodes():
            if dest_is_dir:
                # put the current node into base
                dest_parts.append(get_parts(src_node)[-1])

            # check for conflicts with existing runs
            dest_route = Route(dest_parts)
            if dest_route.node() is not None:
                dest_route.already_exists()

            for child_run_node in findall(src_node, lambda n: hasattr(n, COMMIT)):
                stem = get_parts(child_run_node)[len(get_parts(src_node)):]
                dest_run = runs.run.Run(dest_parts + stem)
                src_run = runs.run.Run(child_run_node)
                moves.append((src_run, dest_run))

        prompt = ("Planned moves:\n\n" +
                  '\n'.join(s.path + ' -> ' + d.path for s, d in moves) +
                  '\n\nContinue?')
        if assume_yes or get_permission(prompt):
            for src, dest in moves:
                assert isinstance(src, runs.run.Run)
                assert isinstance(dest, runs.run.Run)
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
