from contextlib import contextmanager

from runs.db import open_db


class Root:
    @contextmanager
    def open_root(self):
        with open_db(self.root, self.cfg.db_path) as root:
            yield root
