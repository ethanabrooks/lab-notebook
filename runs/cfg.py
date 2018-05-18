from pathlib import Path

from runs.util import _exit


class Cfg:
    def __init__(self,
                 root,
                 db_path,
                 hidden_columns=None,
                 dir_names=None,
                 prefix=None,
                 flags=None,
                 quiet=False):
        self.root = Path(root).expanduser()
        self.db_path = Path(db_path).expanduser()
        should_be_absolute = '`{}` ({}) should be absolute.'
        if not self.root.is_absolute():
            _exit(should_be_absolute.format('root', self.root))
        if not self.db_path.is_absolute():
            _exit(should_be_absolute.format('db_path', self.db_path))
        if not prefix:
            prefix = ''
        self.prefix = prefix.replace('~', str(Path('~').expanduser())) + ' '
        self.dir_names = dir_names.split() if dir_names else []
        self.hidden_columns = hidden_columns.split() if hidden_columns else []
        self.flags = flags
        self.quiet = quiet
