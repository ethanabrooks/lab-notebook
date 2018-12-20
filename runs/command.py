import itertools
import re
from enum import Enum, auto
from typing import List, Set, Union, Generator


class Type(Enum):
    ADDED = auto()
    DELETED = auto()
    UNCHANGED = auto()


class Command:
    def __init__(self, *args, path):
        self.path = path

        def iterator():
            for argstring in args:
                if argstring:
                    assert isinstance(argstring, str)
                    yield from re.split('\s+', argstring)

        groupby = itertools.groupby(iterator(), lambda s: s.startswith('-'))
        self.arg_groups = [set(v) if k else list(v) for k, v in groupby]

    def __str__(self):

        def iterator() -> Generator[str, None, None]:
            for v in self.arg_groups:
                yield from v

        return ' '.join(iterator()).replace('<path>', str(self.path))

    def diff(self, other):
        def regroup(groups: List[Union[List[str], Set[str]]]):
            for positional, nonpositional in zip(groups[0::2], groups[1::2]):
                assert isinstance(positional, list), \
                    "Command should not start with a nonpositional argument (Command: " \
                    f"{self})"
                for positional1, positional2 in itertools.zip_longest(positional,
                                                                      positional[1:]):
                    yield positional1, nonpositional if positional2 is None else set()

        assert isinstance(other, Command)

        for (positional1, nonpositional1), (positional2, nonpositional2) in zip(regroup(
                self.arg_groups), regroup(other.arg_groups)):
            if positional1 == positional2:
                yield positional1, Type.UNCHANGED
            else:
                yield positional1, Type.ADDED
                yield positional2, Type.DELETED
            assert isinstance(nonpositional1, set)
            assert isinstance(nonpositional2, set)
            for blob in nonpositional1 & nonpositional2:
                yield blob, Type.UNCHANGED
            for blob in nonpositional1 - nonpositional2:
                yield blob, Type.ADDED
            for blob in nonpositional2 - nonpositional1:
                yield blob, Type.DELETED
