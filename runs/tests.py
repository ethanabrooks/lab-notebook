import os
import shutil
import subprocess
from pathlib import Path
from unittest import TestCase

import yaml

from runs import main
from runs.run import Run


def sessions():
    return subprocess.check_output(
        'tmux list-session -F "#{session_name}"'.split(),
        universal_newlines=True).split('\n')


class TestRuns(TestCase):
    path = '/tmp/test-run-manager'
    run_name = 'test-run'

    def setUp(self):
        Path(TestRuns.path).mkdir(exist_ok=True)
        os.chdir(TestRuns.path)
        subprocess.run(['git', 'init', '-q'], cwd=TestRuns.path)
        with Path(TestRuns.path, '.gitignore').open('w') as f:
            f.write('.runsrc\nruns.yml')
        subprocess.run(['git', 'add', '.gitignore'], cwd=TestRuns.path)
        subprocess.run(['git', 'commit', '-qam', 'init'], cwd=TestRuns.path)

    def tearDown(self):
        shutil.rmtree(TestRuns.path)


class TestNew(TestRuns):
    def setUp(self):
        super().setUp()
        self.name = 'test-run'
        self.command = 'echo hello'
        self.description = 'test new command'
        main.main(['new', self.name, self.command,
                   "--description=" + self.description, '-q'])

    def tearDown(self):
        Run(TestRuns.run_name).kill_tmux()
        super().tearDown()

    def test_db(self):
        with Path(TestRuns.path, 'runs.yml').open() as f:
            db = yaml.load(f)
        assert 'commit' in db
        assert 'datetime' in db
        assert db['description'] == self.description
        assert db['full_command'] == self.command
        assert db['input_command'] == self.command
        assert db['name'] == self.name

    def test_tmux(self):
        assert '"' + TestRuns.run_name + '"' in sessions()


class TestNewWithConfig(TestNew):
    def setUp(self):
        self.dir_names = ['checkpoints', 'tensorboard']
        self.root = '.runs'
        Path(TestRuns.path).mkdir()
        with Path(TestRuns.path, '.runsrc').open('w') as f:
            f.write(
                """\
[DEFAULT]
root = {}
db_path = runs.yml
dir_names = {}\
""".format(self.root, ' '.join(self.dir_names)))
        super().setUp()

    def test_mkdirs(self):
        for dir_name in self.dir_names:
            assert Path(TestRuns.path, self.root, dir_name, self.name).exists()


# class TestRemoveNoPattern(TestNew):
#     def setUp(self):
#         super().setUp()
#         main.main(['rm', self.name])
#
#     def test_tmux(self):
#         assert '"' + TestRuns.run_name + '"' not in sessions()
#
#     def test_rmdirs(self):
#         for root, dirs, files in os.walk(TestRuns.path):
#             for file in files:
#                 assert self.name != file
