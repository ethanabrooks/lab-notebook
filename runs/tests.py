import argparse
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
        output = subprocess.check_output('tmux list-session -F "#{session_name}"'.split(),
                                         universal_newlines=True)
        assert isinstance(output, str)
        return output.split('\n')
    except subprocess.CalledProcessError:
        return []


class TestBase(TestCase):
    def setUp(self):
        Path(self.path).mkdir(exist_ok=True)
        os.chdir(self.path)
        subprocess.run(['git', 'init', '-q'], cwd=self.path)
        with Path(self.path, '.gitignore').open('w') as f:
            f.write('.runsrc\nruns.yml')
        subprocess.run(['git', 'add', '.gitignore'], cwd=self.path)
        subprocess.run(['git', 'commit', '-qam', 'init'], cwd=self.path)
        self.input_command = 'python -c "{}"'.format(
            """\
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--option', default=0)
print(vars(parser.parse_args()))\
""")
        self.description = 'test new command'

    def tearDown(self):
        shutil.rmtree(self.path)

    @property
    def path(self):
        return '/tmp/test-run-manager'

    @property
    def name(self):
        return 'test_run'


class TestNew(TestBase):
    def setUp(self):
        super().setUp()
        main.main(['new', self.name, self.input_command,
                   "--description=" + self.description, '-q'])

    @property
    def full_command(self):
        return self.input_command

    def tearDown(self):
        Run(self.name).kill_tmux()
        super().tearDown()

    def test_tmux(self):
        self.assertIn('"' + self.name + '"', sessions())

    def test_db(self):
        with Path(self.path, 'runs.yml').open() as f:
            db = yaml.load(f)['children'][0]
        for key in ['commit', 'datetime']:
            with self.subTest(key=key):
                self.assertIn(key, db)
        for key in ['description', 'full_command', 'name']:
            with self.subTest(key=key):
                self.assertEqual(db[key], getattr(self, key))
        key = 'input_command'
        with self.subTest(key=key):
            self.assertEqual(db[key], self.input_command)


# class TestNewWithSubdir(TestNew):
#     @property
#     def name(self):
#         return 'subdir/test_run'
#
#     def test_db(self):
#         # TODO
#         with open('runs.yml') as f:
#             print(f.read())
#         super().test_db()


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
            self.assertTrue(path.exists())

    def test_db(self):
        super().test_db()

    @property
    def full_command(self):
        return self.input_command + ' --option=1'


# class TestNewWithSubdirAndConfig(TestNewWithConfig, TestNewWithSubdir):
#     pass


class TestRemoveNoPattern(TestNew):
    def setUp(self):
        super().setUp()
        main.main(['rm', '-y', self.name])

    def test_tmux(self):
        self.assertNotIn('"' + self.name + '"', sessions())

    def test_rmdirs(self):
        for root, dirs, files in os.walk(self.path):
            for file in files:
                with self.subTest(file=file):
                    self.assertNotEqual(self.name, file)


class TestList(TestNew):
    def test_list(self):
        for pattern in ['*', 'test*']:
            with self.subTest(pattern=pattern):
                string = Pattern(pattern).tree_string(print_attrs=False)
                self.assertEqual(string, """\
.
└── test_run
""")
        pattern = 'x*'
        with self.subTest(pattern=pattern):
            with self.assertRaises(SystemExit):
                Pattern(pattern).tree_string()


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
