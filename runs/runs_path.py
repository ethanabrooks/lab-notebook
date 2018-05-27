from pathlib import PurePath
from typing import Optional

from anytree import ChildResolverError, NodeMixin, Resolver

from runs.config import Config


class RunsPath(PurePath):
    config = None

    @property
    def cfg(self) -> Config:
        if RunsPath.config is None:
            raise RuntimeError('RunsPath.cfg is not set.')
        return RunsPath.config

    def node(self, root: NodeMixin) -> Optional[NodeMixin]:
        """
         Get the node corresponding to this path if it exists.
        Otherwise return None.
         """
        try:
            return Resolver().get(root, self.is_absolute())
        except ChildResolverError:
            return None

    def nodes(self, root: NodeMixin):
        try:
            # if self.path is '.':
            #     return list(PreOrderIter(root))
            return Resolver().glob(root, self)
        except ChildResolverError:
            return []

    def exists(self, root: NodeMixin):
        self.node(root) is not None
