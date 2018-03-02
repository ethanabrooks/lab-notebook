import os
import shutil
import subprocess
from pathlib import Path
from unittest import TestCase

import yaml

from runs import main
from runs.run import Run


class TestRuns(TestCase):
    path = '/tmp/test-run-manager'
    run_name = 'test-run'

    def setUp(self):
        Path(TestRuns.path).mkdir()
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
        self.command = 'python -c "print(\\"hello\\")"'
        self.description = 'test new command'
        main.main(['new', self.name, self.command,
                   "--description="+self.description, '-q'])

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
        sessions = subprocess.check_output(
            'tmux list-session -F "#{session_name}"'.split(),
            universal_newlines=True)
        assert '"' + TestRuns.run_name + '"' in sessions.split('\n')
