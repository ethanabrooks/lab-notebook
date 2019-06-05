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

        argstring = ' '.join([a for a in args if a is not None])
        reg = '[\'"\s=]+'
        words = re.split(reg, argstring)
        seps = re.findall(reg, argstring)

        self.positionals = []
        self.optionals = []
        self.flags = []
        key = None
        value = []

        pairs = [(a, b) for (a, b) in itertools.zip_longest(words, seps) if a]

        def is_value(string):
            try:
                float(string)
                return True
            except ValueError:
                return not string.startswith('-')

        for (word1, sep), word2 in itertools.zip_longest(pairs, pairs[1:]):
            if word2 is not None:
                word2, sep2 = word2
            if is_value(word1):
                if key is None:
                    self.positionals.append((word1, sep))
                else:
                    value.append((word1, sep))
            else:  # nonpositional or flag
                if word2 is not None and is_value(word2):
                    key = (word1, sep)
                    value = []
                else:
                    self.flags.append((word1, sep))

            # store key/value
            if key is not None and (word2 is None or not is_value(word2)):
                self.optionals.append((key, value))
                key = None
                value = []

    def positional_strings(self):
        for w, s in self.positionals:
            s = s or ' '
            yield w + s

    def flag_strings(self):
        for w, s in self.flags:
            s = s or ' '
            yield w + s

    def optional_strings(self):
        for (k, ks), v in self.optionals:

            def value_iterator():
                for (vw, vs) in v:
                    yield vw
                    if vs is None:
                        yield ' '
                    else:
                        yield vs

            yield k + ks + ''.join(value_iterator())

    def __str__(self):
        def iterator():
            yield from self.positional_strings()
            yield from sorted(self.flag_strings())
            yield from sorted(self.optional_strings())

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
        for (positional1, s1), (positional2, s2) in zip(
                zip(self.positionals, self.positional_strings()),
                zip(other.positionals, other.positional_strings())):
            if positional1 == positional2:
                yield s1, Type.UNCHANGED
            else:
                yield s1, Type.ADDED
                yield s2, Type.DELETED

        def make_hashable(k, v):
            return k, tuple(v)

        our_optionals = set([make_hashable(*p) for p in self.optionals])
        their_optionals = set([make_hashable(*p) for p in other.optionals])

        for o, s in zip(self.optionals, self.optional_strings()):
            if make_hashable(*o) in their_optionals:
                yield s, Type.UNCHANGED
            else:
                yield s, Type.ADDED
        for o in other.optionals:
            if make_hashable(*o) not in our_optionals:
                yield s, Type.DELETED

        our_flags = set(self.flags)
        their_flags = set(other.flags)

        for o, s in zip(self.flags, self.flag_strings()):
            if o in their_flags:
                yield s, Type.UNCHANGED
            else:
                yield s, Type.ADDED
        for o in other.flags:
            if o not in our_flags:
                yield s, Type.DELETED

    def exclude(self, *args):
        exclude_command = Command(*args, path=None)
        new_command = copy.deepcopy(self)

        def positionals():
            for p, p_exclude in itertools.zip_longest(
                    new_command.positionals,
                    exclude_command.positionals,
            ):
                if p is not None and p != p_exclude:
                    yield p

        def optionals():
            exclude = set(k for k, v in exclude_command.optionals)
            for (k, v) in self.optionals:
                if k not in exclude:
                    yield k, v

        def flags():
            exclude = set(exclude_command.flags)
            for f in self.flags:
                if f not in exclude:
                    yield f

        new_command.positionals = list(positionals())
        new_command.optionals = list(optionals())
        new_command.flags = list(flags())
        return new_command
