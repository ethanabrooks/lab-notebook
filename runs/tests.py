import os
import shutil
import subprocess
from pathlib import Path
from unittest import TestCase

import yaml

from runs import main
from runs.run import Run


def sessions():
    try:
        return subprocess.check_output(
            'tmux list-session -F "#{session_name}"'.split(),
            universal_newlines=True).split('\n')
    except subprocess.CalledProcessError:
        return []


class TestRuns(TestCase):
    path = '/tmp/test-run-manager'
    run_name = 'test_run'

    def setUp(self):
        TestRuns.path = '/tmp/test-run-manager'
        TestRuns.run_name = 'test_run'
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
        self.command = 'echo hello'
        self.description = 'test new command'
        main.main(['new', TestRuns.run_name, self.command,
                   "--description=" + self.description, '-q'])

    def tearDown(self):
        Run(TestRuns.run_name).kill_tmux()
        super().tearDown()

    def test_db(self):
        with Path(TestRuns.path, 'runs.yml').open() as f:
            db = yaml.load(f)['children'][0]
        assert 'commit' in db
        assert 'datetime' in db
        assert db['description'] == self.description
        assert db['full_command'] == self.command
        assert db['input_command'] == self.command
        assert db['name'] == TestRuns.run_name

    def test_tmux(self):
        assert '"' + TestRuns.run_name + '"' in sessions()


class TestNewWithConfig(TestNew):
    def setUp(self):
        self.dir_names = ['checkpoints', 'tensorboard']
        self.root = '.runs'
        Path(TestRuns.path, TestRuns.run_name).mkdir(parents=True)
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
            assert Path(TestRuns.path, self.root, dir_name, TestRuns.run_name).exists()


class TestRemoveNoPattern(TestNew):
    def setUp(self):
        super().setUp()
        main.main(['rm', '-y', TestRuns.run_name])

    def test_tmux(self):
        assert '"' + TestRuns.run_name + '"' not in sessions()

    def test_rmdirs(self):
        for root, dirs, files in os.walk(TestRuns.path):
            for file in files:
                assert TestRuns.run_name != file
