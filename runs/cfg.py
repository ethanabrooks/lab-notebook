from pathlib import Path

from runs.util import _exit


class Cfg:
    def __init__(self, root, db_path, hidden_columns=None, dir_names=None,
                 virtualenv_path=None, flags=None, quiet=False):
        if flags is None:
            flags = {}
        self.root = Path(root)
        self.db_path = Path(db_path)
        should_be_absolute = '`{}` ({}) should be absolute.'
        if not self.root.is_absolute():
            _exit(should_be_absolute.format('root', self.root))
        if not self.db_path.is_absolute():
            _exit(should_be_absolute.format('db_path', self.db_path))
        self.virtualenv_path = virtualenv_path
        self.dir_names = dir_names.split() if dir_names else []
        self.hidden_columns = hidden_columns.split() if hidden_columns else []
        self.flags = [k if v is None else k + '=' + v
                      for k, v in flags.items()]
        self.quiet = quiet
