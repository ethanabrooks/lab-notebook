# stdlib
from collections import namedtuple
from typing import Tuple


class RunEntry(
        namedtuple('RunEntry', [
            'path',
            'command',
            'commit',
            'datetime',
            'description',
        ])):
    __slots__ = ()

    class KeyError(KeyError):
        pass

    def __str__(self):
        # noinspection PyUnresolvedReferences
        return ','.join([f"'{x}'" for x in self])

    def replace(self, **kwargs):
        return super()._replace(**kwargs)

    @staticmethod
    def fields() -> Tuple[str]:
        return RunEntry(*RunEntry._fields)

    def asdict(self) -> dict:
        return self._asdict()

    def get(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise RunEntry.KeyError
