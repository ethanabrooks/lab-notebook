from collections import defaultdict
from copy import copy
from itertools import zip_longest
from typing import List

from runs.database import DataBase, add_query_flags, DEFAULT_QUERY_FLAGS
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import PurePath


def add_subparser(subparsers):
    parser = subparsers.add_parser('ls', help='Print paths in run database.')

    default_flags = copy(DEFAULT_QUERY_FLAGS)
    default_flags['patterns'].update(default='%', nargs='*')
    add_query_flags(parser, with_sort=True, default_flags=default_flags)

    parser.add_argument(
        '--show-attrs',
        action='store_true',
        help='Print run attributes in addition to names.')
    parser.add_argument('--depth', type=int, help='Depth of tree to print.')
    parser.add_argument(
        '--porcelain',
        action='store_true',
        help='Print list of path names without tree '
        'formatting.')
    return parser


@DataBase.open
@DataBase.query
def cli(runs: List[RunEntry], logger: Logger, porcelain: bool, depth, *args, **kwargs):
    logger.print(string(
        runs=runs,
        porcelain=porcelain,
        depth=depth,
    ))


def string(runs: List[RunEntry], porcelain: bool = True, depth: int = None) -> str:
    return '\n'.join(map(str, paths(runs=runs, porcelain=porcelain, depth=depth)))


def paths(runs: List[RunEntry], porcelain: bool = True, depth: int = None) -> List[str]:
    _paths = [e.path for e in runs]
    return _paths if porcelain else tree_strings(build_tree(_paths), depth=depth)


def build_tree(paths, depth: int = None):
    aggregator = defaultdict(list)
    for path in paths:
        try:
            head, *tail = PurePath(path).parts
        except ValueError:
            return dict()
        if tail:
            head += '/'
        aggregator[head].append(PurePath(*tail))

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
                    depth=None if depth is None else depth - 1):
                yield PurePath(s)
