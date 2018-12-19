import itertools
import re
from collections import namedtuple
from typing import List, Set, Union, Generator

from runs.util import GREEN, RED, RESET

Diff = namedtuple('Diff', 'added deleted')


class Command:
    def __init__(self, *args, path):
        self.path = path

        def arg_iterator():
            for argstring in args:
                if argstring:
                    assert isinstance(argstring, str)
                    yield from re.split('\s+', argstring)

        groupby = itertools.groupby(arg_iterator(), lambda s: s.startswith('-'))
        self.arg_groups = [set(v) if k else list(v) for k, v in groupby]

    def __str__(self):

        def arg_iterator() -> Generator[str, None, None]:
            for v in self.arg_groups:
                yield from v

        return ' '.join(arg_iterator()).replace('<path>', str(self.path))

    def diff(self, other):
        def diffstring(added, deleted):
            return GREEN + added + RED + deleted + RESET

        def regroup(groups: List[Union[str, Set[str]]]):
            for nonpositional, positional in zip(groups[0::2], groups[1::2]):
                for arg in nonpositional[:-1]:
                    yield arg, set()
                yield nonpositional[-1], positional

        assert isinstance(other, Command)
        for g1, g2 in zip(self.arg_groups, other.arg_groups):

            for a1, a2 in itertools.zip_longest(g1, g2):
                if isinstance(a1, str) and isinstance(g2, str):
                    if g1 == g2:
                        yield g1
                    else:
                        yield diffstring(g1, g2)
                elif isinstance(g1, str) and not isinstance(g2, str):
                    yield diffstring(g1)


class DiffCommand(Command):
    @staticmethod
    def atomize(arg):
        if isinstance(arg, Diff):
            return arg
        return super().atomize(arg)

    @staticmethod
    def convert_to_string(arg):
        if isinstance(arg, Diff):
            return GREEN + arg.added + RED + arg.deleted + RESET
        return super().convert_to_string(arg)

    def __str__(self):
        pass
