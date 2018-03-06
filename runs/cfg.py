from pathlib import Path


class Cfg:
    def __init__(self, root, db_path, hidden_columns=None, dir_names=None,
                 virtualenv_path=None, flags=None, quiet=False):
        if flags is None:
            flags = {}
        self.db_path = Path(db_path)
        self.root = Path(root)
        self.virtualenv_path = Path(virtualenv_path) if virtualenv_path else None
        self.dir_names = dir_names.split() if dir_names else []
        self.hidden_columns = hidden_columns.split() if hidden_columns else []
        self.flags = [k if v is None else k + '=' + v
                      for k, v in flags.items()]
        self.quiet = quiet
