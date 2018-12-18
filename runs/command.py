from pathlib import PurePath
from typing import Iterable


class Command:
    def __init__(self, positional: str, nonpositional: Iterable[str], path: PurePath,
                 prefix: str = None):
        self.positional = positional
        self.positional = f'{prefix} {positional}' if prefix else positional
        self.nonpositional = set(nonpositional)
        self.path = path

    def __str__(self):
        return ' '.join([self.positional] + list(self.nonpositional)).replace(
            '<path>', str(self.path))

    def diff(self, other):
        assert isinstance(other, Command)
