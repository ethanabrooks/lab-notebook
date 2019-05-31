import itertools
import re
from enum import Enum, auto
from typing import Generator, List, Set, Union


class Type(Enum):
    ADDED = auto()
    DELETED = auto()
    UNCHANGED = auto()


class Command:
    def __init__(self, *args, path):
        def word_iterator():
            for argstring in args:
                assert isinstance(argstring, str)
                words = re.split('\s+|=', argstring)
                seps = re.findall('\s+|=', argstring) \
                        + [' ']  # pretend all commands end with whitespace
                yield from zip(words, seps)

        self.positionals = []
        self.nonpositionals = dict()
        self.flags = set()
        key = None

        words = list(word_iterator())
        for (word1, sep), word2 in itertools.zip_longest(words, words[1:]):
            if word2 is not None:
                word2, sep2 = word2
            if word1.startswith('-'):  # nonpositional or flag
                if word2 is None or word2.startswith('-'):
                    self.flags.add((word1, sep))
                else:
                    key = (word1, sep)
                    self.nonpositionals[key] = []

            else:  # positional or value
                if key is None:
                    self.positionals.append((word1, sep))
                else:
                    self.nonpositionals[key].append((word1, sep))

        self.args = (
            self.positionals + sorted(self.nonpositionals.items()) + sorted(self.flags))

    def __str__(self):
        return ''.join([s for t in self.positionals for s in t]).replace(
            '<path>', str(self.path))

    @staticmethod
    def from_run(run):
        return Command(run.command, path=run.path)

    @staticmethod
    def from_db(db, path):
        run, = db[path]
        assert path == run.path
        return Command.from_run(run)

    def diff(self, other):
        for positional1, positions2 in zip(self.positionals, other.positionals):
            if positional1 == positional2:
                yield positional1, Type.UNCHANGED
            else:
                yield positional1, Type.ADDED
                yield positional2, Type.DELETED

        nonpositionals1 = set(self.nonpositionals.items()) | self.flags
        nonpositionals2 = set(other.nonpositionals.items()) | other.flags

        for blob in nonpositional1 & nonpositional2:
            yield blob, Type.UNCHANGED
        for blob in nonpositional1 - nonpositional2:
            yield blob, Type.ADDED
        for blob in nonpositional2 - nonpositional1:
            yield blob, Type.DELETED
