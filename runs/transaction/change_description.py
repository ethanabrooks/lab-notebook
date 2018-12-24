# stdlib
from collections import namedtuple

# first party
from runs.transaction.sub_transaction import SubTransaction
from runs.util import string_from_vim

DescriptionChange = namedtuple('DescriptionChange',
                               ['path', 'command', 'old_description', 'new_description'])


class ChangeDescriptionTransaction(SubTransaction):
    def add(self, description_change):
        assert isinstance(description_change, DescriptionChange)
        self.queue.add(description_change)

    def validate(self):
        def get_description(change):
            new_description = string_from_vim(
                f"""
        Edit description for {change.path}.
        Command: {change.command}
        """, change.old_description)
            # noinspection PyProtectedMember
            return change._replace(new_description=new_description)

        self.queue = {c if c.new_description else get_description(c) for c in self.queue}

    def process(self, change: DescriptionChange):
        self.db.update(change.path, description=change.new_description)
