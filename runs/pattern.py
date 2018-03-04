from contextlib import contextmanager
from copy import deepcopy

import yaml
from anytree import RenderTree
from anytree import Resolver, findall
from tabulate import tabulate

import runs.main
from runs.db import DBPath
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
        run_nodes = [node
                     for base in Resolver().glob(root, self.path)
                     for node in findall(base, lambda n: hasattr(n, 'commit'))]
        if not run_nodes:
            print('No runs match pattern, {}. Recorded runs:'.format(self.path))
            print(Pattern('*').tree_string().encode('utf-8'))
            exit()
        return run_nodes

    def names(self):
        return [node.name for node in self.nodes()]

    @property
    def keys(self):
        return set([key for run in self.runs() for key in run.keys])

    def remove(self, assume_yes):
        prompt = 'Remove the following runs?\n{}\n'.format('\n'.join(self.names()))
        if assume_yes or get_permission(prompt):
            with self.open() as runs:
                for run in runs:
                    run.remove()

    def move(self, dest, keep_tmux):
        assert isinstance(dest, runs.run.Run)

        # check for conflicts with existing runs
        if dest.node() is not None:
            dest.already_exists()

        src = self.runs()

        # prompt depends on number of runs being moved
        if len(src) > 1:
            prompt = 'Move the following runs into {}?\n{}'.format(
                dest.work_dir, '\n'.join(run.work_dir for run in src))
        else:
            prompt = 'Move {} to {}?'.format(src[0].work_dir, dest.work_dir)

        if get_permission(prompt):
            for run in src:

                # if the dest exists or we are moving multiple runs,
                if dest.node() is not None or len(src) > 1:
                    # preserve the current name of the run
                    dest = runs.run.Run(dest.work_dir, run.head)

                run.move(dest, keep_tmux)

    def lookup(self, key):
        return [run.lookup(key) for run in self.runs()]

    def tree(self):
        tree = deepcopy(self.read())
        for node in findall(tree, lambda n: n not in self.nodes(tree)):
            node.parent = None
        return tree

    def tree_string(self, print_attrs=False):
        string = ''
        tree = self.tree()
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

    def table(self, column_width):
        def get_values(node, key):
            try:
                value = str(getattr(node, key))
                if len(value) > column_width:
                    value = value[:column_width] + '...'
                return value
            except AttributeError:
                return '_'

        headers = sorted(set(self.keys) - set(self.cfg.hidden_columns))
        table = [[node.name] + [get_values(node, key) for key in headers]
                 for node in sorted(self.nodes(), key=lambda n: n.name)]
        return tabulate(table, headers=headers)

    def reproduce(self):
        if self.nodes():
            return 'To reproduce:\n' + \
                   highlight('git checkout {}\n'.format(self.lookup(COMMIT))) + \
                   highlight("runs new {} '{}' --no-overwrite --description='{}'".format(
                       self.lookup(NAME), self.lookup(COMMAND), self.lookup(DESCRIPTION)))
