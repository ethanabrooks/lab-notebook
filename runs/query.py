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

    @abstractmethod
    def __str__(self):
        raise NotImplementedError

    @abstractmethod
    def values(self):
        raise NotImplementedError


class Predicate(Condition):
    def __init__(self, column, value):
        self.column = column
        self.value = value

    def values(self):
        return [self.value]

    @abstractmethod
    def __str__(self):
        raise NotImplementedError


class Like(Predicate):
    def __str__(self):
        return f'{self.column} LIKE ?'


class Equals(Predicate):
    def __str__(self):
        return f'{self.column} = ?'


class In(Predicate):
    def __str__(self):
        return f'{self.column} IN ({",".join(["?" for _ in self.value])})'


class Operator(Condition):
    def __init__(self, *conditions):
        for condition in conditions:
            assert isinstance(condition, (Operator, Predicate))
        self.conditions = conditions

    def values(self):
        return [value for condition in self.conditions for value in condition.values()]

    @abstractmethod
    def __str__(self):
        pass


class Or(Operator):
    def __str__(self):
        return ' OR '.join(map(str, self.conditions))


class And(Operator):
    def __str__(self):
        return ' AND '.join(map(str, self.conditions))


Any = Or
All = And


class Not(Operator):
    def __init__(self, condition):
        super().__init__(condition)

    def __str__(self):
        return f'NOT {self.conditions}'
