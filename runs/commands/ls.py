from collections import defaultdict
from itertools import zip_longest
from typing import List

from runs.database import DataBase
from runs.logger import Logger
from runs.util import RunPath

help = 'Only display paths matching this pattern.'


def add_subparser(subparsers):
    parser = subparsers.add_parser('ls', help='Print paths in run database.')
    parser.add_argument('patterns', nargs='*', help=help, type=RunPath)
    parser.add_argument(
        '--show-attrs',
        action='store_true',
        help='Print run attributes in addition to names.')
    parser.add_argument(
        '--depth',
        type=int,
        help='Depth of tree to print.')
    parser.add_argument(
        '--porcelain',
        action='store_true',
        help='Print list of path names without tree '
        'formatting.')
    parser.add_argument(
        '--unless', nargs='*', type=RunPath, help='Exclude these paths from the search.')
    return parser


@Logger.wrapper
@DataBase.wrapper
def cli(patterns: List[RunPath], unless: List[RunPath], db: DataBase, porcelain: bool,
        depth, *args, **kwargs):
    db.logger.print(string(*patterns, db=db, porcelain=porcelain, unless=unless,
                           depth=depth,))


def string(*patterns, db: DataBase, porcelain: bool = True,
           unless: List[RunPath] = None, depth: int = None) -> str:
    return '\n'.join(
        map(str, paths(*patterns, db=db, porcelain=porcelain, unless=unless, depth=depth)))


def paths(*patterns, db: DataBase, porcelain: bool = True,
          unless: List[RunPath] = None, depth: int = None) -> List[str]:
    entries = db.get(
        patterns, unless=unless) if patterns else db.all(unless=unless)
    _paths = [e.path for e in entries]
    return _paths if porcelain else tree_strings(build_tree(_paths), depth=depth)


def build_tree(paths, depth: int = None):
    aggregator = defaultdict(list)
    for path in paths:
        try:
            head, *tail = RunPath(path).parts
        except ValueError:
            return dict()
        if tail:
            head += '/'
        aggregator[head].append(RunPath(*tail))

    return {k: build_tree(v, depth=depth) for k, v in aggregator.items()}


def tree_strings(tree, prefix='', root_prefix='', root='.', depth=None):
    yield prefix + root_prefix + root
    if root_prefix == '├── ':
        prefix += '│   '
    if root_prefix == '└── ':
        prefix += '    '
    if tree and (depth is None or depth > 0):
        items = _, *tail = tree.items()
        for (root, tree), _next in zip_longest(items, tail):
            for s in tree_strings(
                    tree=tree,
                    prefix=prefix,
                    root_prefix='├── ' if _next else '└── ',
                    root=root,
                    depth=None if depth is None else depth - 1
            ):
                yield RunPath(s)
