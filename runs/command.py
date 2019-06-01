import copy
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
        self.path = path

        argstring = ' '.join(args)
        reg = '[\'"\s=]+'
        words = re.split(reg, argstring)
        seps = re.findall(reg, argstring) \
                + [' ']  # pretend all commands end with whitespace

        self.positionals = []
        self.nonpositionals = dict()
        self.flags = set()
        key = None

        words = list(zip(words, seps))

        def is_value(string):
            try:
                float(string)
                return True
            except ValueError:
                return not string.startswith('-')

        for (word1, sep), word2 in itertools.zip_longest(words, words[1:]):
            if word2 is not None:
                word2, sep2 = word2
            if is_value(word1):
                if key is None:
                    self.positionals.append((word1, sep))
                else:
                    self.nonpositionals[key].append((word1, sep))
            else:  # nonpositional or flag
                if word2 is not None and is_value(word2):
                    key = (word1, sep)
                    self.nonpositionals[key] = []
                else:
                    self.flags.add((word1, sep))

        nonpositionals = [(k, p) for k, v in self.nonpositionals.items() for p in v]
        self.args = (self.positionals + sorted(nonpositionals) + sorted(self.flags))

    def __str__(self):
        def iterator():
            for w, s in self.positionals + sorted(self.flags):
                yield w
                yield s

            for (k, ks), v in sorted(self.nonpositionals.items()):
                for (vw, vs) in v:
                    yield k
                    yield ks
                    yield vw
                    yield vs

        return ''.join(map(str, iterator())).replace('<path>', str(self.path))

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

    def exclude(self, *args):
        exclude_command = Command(*args, path=None)
        new_command = copy.deepcopy(self)
        new_command.positionals = [
            p1 for p1, p2 in itertools.zip_longest(
                new_command.positionals,
                exclude_command.positionals,
            ) if p1 != p2
        ]
        for k in exclude_command.nonpositionals:
            del new_command.nonpositionals[k]
        new_command.flags -= exclude_command.flags
        return new_command
