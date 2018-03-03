import os
import shutil
import subprocess
from pathlib import Path
from pprint import pprint
from unittest import TestCase

import yaml

from runs import main
from runs.run import Run


def sessions():
    return subprocess.check_output(
        'tmux list-session -F "#{session_name}"'.split(),
        universal_newlines=True).split('\n')


class TestRuns(TestCase):

    def setUp(self):
        self.path = '/tmp/test-run-manager'
        self.run_name = 'test_run'
        Path(self.path).mkdir(exist_ok=True)
        os.chdir(self.path)
        subprocess.run(['git', 'init', '-q'], cwd=self.path)
        with Path(self.path, '.gitignore').open('w') as f:
            f.write('.runsrc\nruns.yml')
        subprocess.run(['git', 'add', '.gitignore'], cwd=self.path)
        subprocess.run(['git', 'commit', '-qam', 'init'], cwd=self.path)

    def tearDown(self):
        shutil.rmtree(self.path)


class TestNew(TestRuns):
    def setUp(self):
        super().setUp()
        self.command = 'echo hello'
        self.description = 'test new command'
        main.main(['new', self.run_name, self.command,
                   "--description=" + self.description, '-q'])

    def tearDown(self):
        Run(self.run_name).kill_tmux()
        super().tearDown()

    def test_db(self):
        with Path(self.path, 'runs.yml').open() as f:
            db = yaml.load(f)['children'][0]
        assert 'commit' in db
        assert 'datetime' in db
        assert db['description'] == self.description
        assert db['full_command'] == self.command
        assert db['input_command'] == self.command
        assert db['name'] == self.run_name

    def test_tmux(self):
        assert '"' + self.run_name + '"' in sessions()


class TestNewWithConfig(TestNew):
    def setUp(self):
        self.dir_names = ['checkpoints', 'tensorboard']
        self.root = '.runs'
        Path(self.path).mkdir()
        with Path(self.path, '.runsrc').open('w') as f:
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
            assert Path(self.path, self.root, dir_name, self.run_name).exists()


class TestRemoveNoPattern(TestNew):
    def setUp(self):
        super().setUp()
        main.main(['rm', '-y', self.run_name])

    # def test_tmux(self):
    #     assert '"' + self.run_name + '"' not in sessions()

    def test_rmdirs(self):
        for root, dirs, files in os.walk(self.path):
            for file in files:
                assert self.run_name != file
