import os
import shutil
import subprocess
from pathlib import Path
from unittest import TestCase

import yaml

from runs import main
from runs.pattern import Pattern
from runs.run import Run


def sessions():
    try:
        return subprocess.check_output(
            'tmux list-session -F "#{session_name}"'.split(),
            universal_newlines=True).split('\n')
    except subprocess.CalledProcessError:
        return []


class TestRuns(TestCase):
    def setUp(self):
        Path(self.path).mkdir(exist_ok=True)
        os.chdir(self.path)
        subprocess.run(['git', 'init', '-q'], cwd=self.path)
        with Path(self.path, '.gitignore').open('w') as f:
            f.write('.runsrc\nruns.yml')
        subprocess.run(['git', 'add', '.gitignore'], cwd=self.path)
        subprocess.run(['git', 'commit', '-qam', 'init'], cwd=self.path)

    def tearDown(self):
        shutil.rmtree(self.path)

    @property
    def path(self):
        return '/tmp/test-run-manager'

    @property
    def name(self):
        return 'test_run'


class TestNew(TestRuns):
    def setUp(self):
        super().setUp()
        self.command = 'python -c "{}"'.format(
            """\
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--option', default=0)
print(vars(parser.parse_args()))\
""")
        self.full_command = self.command
        self.description = 'test new command'
        main.main(['new', self.name, self.command,
                   "--description=" + self.description, '-q'])

    def tearDown(self):
        Run(self.name).kill_tmux()
        super().tearDown()

    def test_tmux(self):
        assert '"' + self.name + '"' in sessions()

    def test_db(self):
        with Path(self.path, 'runs.yml').open() as f:
            db = yaml.load(f)['children'][0]
        for key in ['commit','datetime']:
            with self.subTest(key=key):
                self.assertIn(key, db)
        for key in ['description', 'full_command', 'name']:
            with self.subTest(key=key):
                self.assertEqual(db[key], getattr(self,key))
        key = 'input_command'
        with self.subTest(key=key):
            self.assertEqual(db[key], self.command)


# class TestNewWithSubdir(TestNew):
#     @property
#     def run_name(self):
#         return 'subdir/test_run'
#
#     def test_db(self):
#         self.


class TestNewWithConfig(TestNew):
    def setUp(self):
        self.dir_names = ['checkpoints', 'tensorboard']
        self.root = '.runs'
        Path(self.path, self.name).mkdir(parents=True)
        with Path(self.path, '.runsrc').open('w') as f:
            f.write(
                """\
[filesystem]
root = {}
db_path = runs.yml
dir_names = {}

[flags]
--option=1\
""".format(self.root, ' '.join(self.dir_names)))
        super().setUp()

    def test_mkdirs(self):
        for dir_name in self.dir_names:
            path = Path(self.path, self.root, dir_name, self.name)
            assert path.exists()

    def test_db(self):
        self.full_command = self.command + ' --option=1'
        super().test_db()


class TestRemoveNoPattern(TestNew):
    def setUp(self):
        super().setUp()
        main.main(['rm', '-y', self.name])

    def test_tmux(self):
        self.assertNotIn('"' + self.name + '"', sessions())

    def test_rmdirs(self):
        for root, dirs, files in os.walk(self.path):
            for file in files:
                self.assertNotEqual(self.name, file)


class TestList(TestNew):
    def setUp(self):
        self.pattern = '*'
        super().setUp()

    def test_list(self):
        string = Pattern(self.pattern).tree_string(print_attrs=False)
        self.assertEqual(string, """\
.
└── test_run
""")

    def test_list_happy_pattern(self):
        self.pattern = 'test*'
        self.test_list()

    def test_list_sad_pattern(self):
        self.pattern = 'x*'
        with self.assertRaises(SystemExit):
            self.test_list()


class TestTable(TestNew):
    def test_table(self):
        self.assertIsInstance(Pattern('*').table(100), str)


class TestLookup(TestNew):
    def test_lookup(self):
        self.assertEqual(Pattern('*').lookup('name'), [self.name])


class TestChdesc(TestNew):
    def test_chdescription(self):
        description = 'new description'
        main.main(['chdesc', self.name, '--description=' + description])
        self.assertEqual(Run(self.name).lookup('description'), description)
