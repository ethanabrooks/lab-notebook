# stdlib
from collections import namedtuple
from functools import wraps
from pathlib import PurePath
from typing import List

# first party
from runs.database import DataBase
from runs.file_system import FileSystem
from runs.logger import UI
from runs.run_entry import RunEntry
from runs.shell import Bash
from runs.transaction.change_description import ChangeDescriptionTransaction, DescriptionChange
from runs.transaction.kill import KillTransaction
from runs.transaction.move import Move, MoveTransaction
from runs.transaction.new import NewRunTransaction
from runs.transaction.removal import RemovalTransaction
from runs.transaction.sub_transaction import SubTransaction
from runs.util import natural_order

TransactionType = namedtuple('TransactionType', [
    'description_change',
    'kill',
    'removal',
    'move',
    'new_run',
])


class Transaction:
    @staticmethod
    def wrapper(func):
        @wraps(func)
        def _wrapper(db_path, quiet, assume_yes, root, dir_names, *args, **kwargs):
            ui = UI(assume_yes=assume_yes, quiet=quiet)
            with DataBase(path=db_path, logger=ui) as db:
                transaction = Transaction(
                    ui=ui,
                    db=db,
                    root=root,
                    dir_names=dir_names,
                )
                with transaction as open_transaction:
                    return func(
                        db=db,
                        logger=ui,
                        bash=open_transaction.bash,
                        transaction=open_transaction,
                        *args,
                        **kwargs)

        return _wrapper

    def __init__(self, db: DataBase, ui: UI, root: PurePath, dir_names: List[str]):
        self.ui = ui
        self.db = db
        self.bash = Bash(logger=self.ui)
        file_system = FileSystem(root=root, dir_names=dir_names)
        kwargs = dict(
            ui=self.ui,
            db=self.db,
            bash=self.bash,
            file_system=file_system,
        )

        self.sub_transactions = TransactionType(
            description_change=ChangeDescriptionTransaction(**kwargs),
            kill=KillTransaction(**kwargs),
            removal=RemovalTransaction(**kwargs),
            move=MoveTransaction(**kwargs),
            new_run=NewRunTransaction(**kwargs),
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        def sort(st: SubTransaction):
            st.queue = sorted(st.queue, key=lambda x: natural_order(str(x)))

        def validate(st: SubTransaction):
            st.validate()

        def execute(st: SubTransaction):
            for x in st.queue:
                st.process(x)

        for process in [sort, validate, execute]:
            for sub_transaction in self.sub_transactions:
                assert isinstance(sub_transaction, SubTransaction)
                if sub_transaction.queue:
                    process(sub_transaction)

    def add_run(self, path: PurePath, command: str, commit: str, datetime: str,
                description: str):
        self.sub_transactions.new_run.add(
            RunEntry(
                path=path,
                command=command,
                commit=commit,
                datetime=datetime,
                description=description))

    def move(self, src: PurePath, dest: PurePath, kill_tmux: bool):
        self.sub_transactions.move.add(Move(src=src, dest=dest, kill_tmux=kill_tmux))

    def remove(self, path: PurePath):
        self.sub_transactions.removal.add(path)

    def kill(self, path: PurePath):
        self.sub_transactions.kill.add(path)

    def change_description(self, path: PurePath, command: str, old_description: str,
                           new_description: str):
        self.sub_transactions.description_change.add(
            DescriptionChange(
                path=path,
                command=command,
                old_description=old_description,
                new_description=new_description))
