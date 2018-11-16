# stdlib
from collections import defaultdict
from copy import deepcopy
from itertools import zip_longest
from typing import List

# first party
from runs.database import DEFAULT_QUERY_FLAGS, DataBase, add_query_flags
from runs.logger import Logger
from runs.run_entry import RunEntry
from runs.util import PurePath, natural_order


def add_subparser(subparsers):
    parser = subparsers.add_parser('ls', help='Print paths in run database.')
    add_query_flags(parser, with_sort=True, default_flags=DEFAULT_QUERY_FLAGS)

    parser.add_argument(
        '--show-attrs',
        action='store_true',
        help='Print run attributes in addition to names.')
    parser.add_argument('--depth', type=int, help='Depth of path to print.')
    parser.add_argument(
        '--pprint',
        action='store_true',
        help='format list of path names as tree '
        'formatting.')
    return parser


@DataBase.open
@DataBase.query
def cli(runs: List[RunEntry], logger: Logger, pprint: bool, depth, *args, **kwargs):
    logger.print(string(
        runs=runs,
        pprint=pprint,
        depth=depth,
    ))


def string(runs: List[RunEntry], pprint: bool = False, depth: int = None) -> str:
    return '\n'.join(map(str, paths(runs=runs, pprint=pprint, depth=depth)))


def paths(runs: List[RunEntry], pprint: bool = True, depth: int = None) -> List[str]:
    _paths = [PurePath(*e.path.parts[:depth]) for e in runs]
    if depth is not None:
        _paths = sorted(set(_paths), key=lambda p: natural_order(str(p)))
    return tree_strings(build_tree(_paths)) if pprint else _paths


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
                yield PurePath(s)
