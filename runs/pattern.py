from contextlib import contextmanager
from copy import deepcopy

from anytree import ChildResolverError
from anytree import NodeMixin
from anytree import PreOrderIter
from anytree import Resolver, findall

from runs import db
from runs.db import tree_string
from runs.route import Route
from runs.run import Run
from runs.util import get_permission, is_run_node


class Pattern(Route):
    """
    A Pattern is a Route that may pattern match to multiple objects.
    """
    # DB I/O
    @contextmanager
    def open(self):
        tree = self.read()
        yield self.runs(tree)
        self.write(tree)

    def runs(self, root=None):
        return [
            Run(run) for base in self.nodes(root)
            for run in findall(base, is_run_node)
        ]

    def nodes(self, root=None):
        if root is None:
            root = self.read()
        try:
            if self.path is '.':
                return list(PreOrderIter(root))
            return Resolver().glob(root, self.path.rstrip(self.sep))
        except ChildResolverError:
            return []

    def names(self):
        return [node.name for node in self.nodes()]

    @property
    def paths(self):
        return [
            self.sep.join([n.name for n in node.path])
            for node in self.nodes()
        ]

    @property
    def keys(self):
        return set([key for run in self.runs() for key in run.keys])

    def remove(self, assume_yes):
        prompt = 'Runs to be removed:\n{}\nContinue?'.format(
            '\n'.join(self.paths))
        if assume_yes or get_permission(prompt):
            for run in self.runs():
                run.remove()

    def move(self, dest, kill_tmux, assume_yes):
        assert isinstance(dest, Route)

        multi_move = len(self.nodes()) > 1

        if dest.is_run() and multi_move:
            self.exit(
                "'{}' already exists and '{}' matches the following runs:\n"
                "{}\n"
                "Cannot move multiple runs into an existing run.".format(
                    dest, self.path, '\n'.join(self.paths)))

        def marshall_moves(src_node, dest_route):
            """ Collect moves corresponding to a src node and a dest route """
            assert isinstance(src_node, NodeMixin)

            existing_dir = dest.exists and not dest.is_run()
            non_existing_dir = not dest.exists and (dest.dir_path
                                                    or multi_move)
            if existing_dir or non_existing_dir:
                # put the current node into dest
                dest_route = Route(dest_route.parts + [src_node.path[-1]])

            def dest_run(src_base, src_run):
                stem = src_run.path[len(src_base.path):]
                return Run(dest_route.parts + list(stem))

            # add child runs to moves list
            return [(Run(src_run_node), dest_run(src_node, src_run_node))
                    for src_run_node in findall(src_node, is_run_node)]

        moves = [(s, d) for node in self.nodes()
                 for s, d in marshall_moves(node, dest)]

        # check before moving
        prompt = ("Planned moves:\n\n" + '\n'.join(s.path + ' -> ' + d.path
                                                   for s, d in moves) +
                  '\n\nContinue?')

        if moves and (assume_yes or get_permission(prompt)):

            # check for conflicts with existing runs
            if dest.is_run():
                dest.remove(assume_yes=assume_yes)

            for src, dest in moves:
                src.move(dest, kill_tmux)

    def lookup(self, key):
        return [run.lookup(key) for run in self.runs()]

    def descendants(self):
        return [n for n in PreOrderIter(self.tree()) if n.is_leaf]

    def descendant_strings(self):
        return '\n'.join([
            self.sep.join([n.name for n in d.path])
            for d in self.descendants()
        ])

    def tree(self):
        tree = deepcopy(self.read())
        if self.path == '.':
            return tree
        nodes = self.nodes(tree)

        def not_part_of_tree(node):
            return not any(node is n for n in nodes) and \
                not any(node is d for n in nodes for d in n.descendants)

        for node in findall(tree, not_part_of_tree):
            node.parent = None
        return tree

    def tree_string(self, print_attrs=False):
        return tree_string(tree=self.tree(), print_attrs=print_attrs)

    def table(self, column_width):
        return db.table(self.runs(), self.cfg.hidden_columns, column_width)
