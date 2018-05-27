import yaml
from anytree import NodeMixin
from anytree import RenderTree


class Tree(NodeMixin):
    def string(self, print_attrs: bool) -> str:
        string = ''
        for pre, fill, node in RenderTree(self):
            public_attrs = {k: v for k, v in vars(node).items()}
            if public_attrs:
                pnode = yaml.dump(
                    public_attrs, default_flow_style=False).split('\n')
            else:
                pnode = ''
            string += "{}{}\n".format(pre, node.name)
            if print_attrs:
                for line in pnode:
                    string += "{}{}\n".format(fill, line)
        return string

    def __iadd__(self, other):
        """
        Add a node corresponding to this path to root
        """
        node = self.node(self.root)
        if node:
            return node
        parent = self.parent().add_to_tree(root)
        return Node(name=self.head, parent=parent)
