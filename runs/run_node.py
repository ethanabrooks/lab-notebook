from anytree import NodeMixin


class RunNode(NodeMixin):
    def __init__(self, name, full_command, input_command, commit, datetime, description, parent):
        self.name = name
        self.full_command = full_command
        self.input_command = input_command
        self.commit = commit
        self.datetime = datetime
        self.description = description
        self.parent = parent
