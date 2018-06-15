from collections import defaultdict
from itertools import zip_longest
from pathlib import PurePath
from typing import List

from runs.database import DataBase
from runs.logger import Logger

help = 'Only display paths matching this pattern.'


def add_subparser(subparsers):
    list_parser = subparsers.add_parser('ls', help='List all names in run database.')
    list_parser.add_argument('patterns', nargs='*', help=help, type=PurePath)
    list_parser.add_argument(
        '--show-attrs',
        action='store_true',
        help='Print run attributes in addition to names.')
    list_parser.add_argument(
        '--porcelain',
        action='store_true',
        help='Print list of path names without tree '
        'formatting.')
    list_parser.add_argument(
        '--unless',
        nargs='*',
        type=PurePath,
        help='Print list of path names without tree '
             'formatting.')
    return list_parser


@Logger.wrapper
@DataBase.wrapper
def cli(patterns: List[PurePath], db: DataBase, porcelain: bool, unless: List[PurePath],
        *args, **kwargs):
    db.logger.print(string(*patterns, db=db, porcelain=porcelain, unless=unless))


def string(*patterns, db: DataBase, porcelain: bool = True, unless: List[PurePath] = None) -> str:
    return '\n'.join(map(str, paths(*patterns, db=db, porcelain=porcelain, unless=unless)))


def paths(*patterns, db: DataBase, porcelain: bool = True, unless: List[PurePath] = None) -> List[str]:
    entries = db.descendants(*patterns, unless=unless) if patterns else db.all(unless=unless)
    _paths = [e.path for e in entries]
    return _paths if porcelain else tree_strings(build_tree(_paths))


def build_tree(paths):
    aggregator = defaultdict(list)
    for path in paths:
        try:
            head, *tail = PurePath(path).parts
        except ValueError:
            return dict()
        if tail:
            head += '/'
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
                yield PurePath(s)
