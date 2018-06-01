from collections import defaultdict
from itertools import zip_longest
from pathlib import PurePath

from runs.database import DataBase
from runs.logger import Logger
from runs.util import LIST, PATTERN, nonempty_string

help = 'Only display paths matching this pattern.'


def add_subparser(subparsers):
    list_parser = subparsers.add_parser(LIST, help='List all names in run database.')
    list_parser.add_argument(PATTERN, nargs='?', help=help, type=nonempty_string)
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
@DataBase.wrapper
def cli(pattern, db, porcelain, *args, **kwargs):
    db.logger.print(string(pattern=pattern, db=db, porcelain=porcelain))


def string(pattern, db, porcelain=True):
    return '\n'.join(strings(pattern, db, porcelain))


def strings(pattern, db, porcelain=True):
    entries = db[pattern + '%'] if pattern else db.all()
    paths = [e.path for e in entries]
    return paths if porcelain else tree_strings(build_tree(paths))


def build_tree(paths):
    aggregator = defaultdict(list)
    for path in paths:
        try:
            head, *tail = PurePath(path).parts
        except ValueError:
            return dict()
        aggregator[head].append(PurePath(*tail))
    return {k: build_tree(v) for k, v in aggregator.items()}


def tree_strings(tree, prefix='', root_prefix='', root='.'):
    yield prefix + root_prefix + root
    if root_prefix == '├── ':
        prefix += '│   '
    if root_prefix == '└── ':
        prefix += '    '
    if tree:
        items = _, *tail = tree.items()
        for (root, tree), _next in zip_longest(items, tail):
            for s in tree_strings(
                    tree=tree,
                    prefix=prefix,
                    root_prefix='├── ' if _next else '└── ',
                    root=root):
                    yield s
