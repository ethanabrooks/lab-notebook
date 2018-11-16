# stdlib
from abc import abstractmethod


class Condition:
    def __and__(self, condition):
        assert isinstance(condition, Condition)
        return And(self, condition)

    def __or__(self, condition):
        assert isinstance(condition, Condition)
        return Or(self, condition)

    def __invert__(self):
        return Not(self)

    def __bool__(self):
        return bool(self.values())

    def __str__(self):
        return self._str() if self.values() else ''

    def values(self):
        return [str(v) for v in self._values() if v]

    def _placeholders(self):
        return ','.join('?' * len(self.values()))

    @abstractmethod
    def _str(self):
        raise NotImplementedError

    @abstractmethod
    def _values(self):
        raise NotImplementedError


class OneToManyPredicate(Condition):
    def __init__(self, column, *values):
        self.column = column
        self.__values = values

    def _values(self):
        return self.__values

    def _str(self):
        return f'{self.column} {self._keyword()} ({self._placeholders()})'

    @abstractmethod
    def _keyword(self):
        raise NotImplementedError


class Like(OneToManyPredicate):
    def _keyword(self):
        return 'LIKE'


class In(OneToManyPredicate):
    def _keyword(self):
        return 'IN'


class OneToOnePredicate(OneToManyPredicate):
    def __init__(self, column, value):
        super().__init__(self, column, value)


class Equals(OneToOnePredicate):
    def _keyword(self):
        return '='


class GreaterThan(OneToOnePredicate):
    def _keyword(self):
        return '>'


class LessThan(OneToOnePredicate):
    def _keyword(self):
        return '<'


class ManyToManyPredicate(Condition):
    def __init__(self, *conditions):
        for condition in conditions:
            assert isinstance(condition, Condition)
        self.conditions = [c for c in conditions if c]

    def _values(self):
        return [value for condition in self.conditions for value in condition.values()]

    def _str(self):
        return f' {self._keyword()} '.join(map(str, self.conditions))

    @abstractmethod
    def _keyword(self):
        raise NotImplementedError


class Or(ManyToManyPredicate):
    def _keyword(self):
        return 'OR'


class And(ManyToManyPredicate):
    def _keyword(self):
        return 'AND'


Any = Or
All = And


class Not(Condition):
    def __init__(self, condition):
        assert isinstance(condition, Condition)
        self.condition = condition

    def _str(self):
        return f'NOT {self.condition}'

    def _values(self):
        return self.condition.values()
