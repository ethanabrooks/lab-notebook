from collections import defaultdict
from pathlib import PurePath
from pprint import pprint

from runs.database import Table
from runs.logger import Logger
from runs.util import LIST, PATTERN, nonempty_string

help = 'Only display paths matching this pattern.'


def add_subparser(subparsers):
    list_parser = subparsers.add_parser(
        LIST, help='List all names in run database.')
    list_parser.add_argument(
        PATTERN, nargs='?', help=help, type=nonempty_string)
    list_parser.add_argument(
        '--show-attrs',
        action='store_true',
        help='Print run attributes in addition to names.')
    list_parser.add_argument(
        '--porcelain',
        action='store_true',
        help='Print list of path names without tree '
             'formatting.')
    return list_parser


@Logger.wrapper
@Table.wrapper
def cli(pattern, table, porcelain, *args, **kwargs):
    if pattern:
        entries = table[pattern]
    else:
        entries = table.all()
    paths = [e.path for e in entries]
    if porcelain:
        for string in paths:
            print(string)
    else:
        tree = build_tree(paths)
        pprint(tree)
        for string in tree_strings(tree):
            print(string)


def strings(pattern, table):
    return [e.path for e in table[pattern]]


def build_tree(paths):
    aggregator = defaultdict(list)
    for path in paths:
        try:
            print(path)
            head, *tail = PurePath(path).parts
        except ValueError:
            return dict()
        aggregator[head].append(PurePath(*tail))
    return {k: build_tree(v) for k, v in aggregator.items()}


def tree_strings(tree, prefix='', root_prefix='', root='.'):
    yield prefix + root_prefix + root
    if root_prefix == '├── ':
        prefix += "│   "
    if root_prefix == '└── ':
        prefix += "    "
    if tree:
        *rest, last = tree.items()
        for root, tree in rest:
            for string in tree_strings(tree=tree,
                                       prefix=prefix,
                                       root_prefix='├── ',
                                       root=root):
                yield string
        root, tree = last
        for string in tree_strings(tree=tree,
                                   prefix=prefix,
                                   root_prefix='└── ',
                                   root=root):
            yield string

