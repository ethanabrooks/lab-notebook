import argparse
import os
import shutil
import subprocess
from pathlib import Path
from pprint import pprint
from unittest import TestCase

import yaml

from runs import main
from runs.pattern import Pattern
from runs.run import Run
from runs.util import NAME

CHILDREN = 'children'


def get_name(nodes, name):
    return next(n for n in nodes if n[NAME] == name)


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
        Path(self.work_dir).mkdir(exist_ok=True)
        os.chdir(self.work_dir)
        subprocess.run(['git', 'init', '-q'], cwd=self.work_dir)
        with Path(self.work_dir, '.gitignore').open('w') as f:
            f.write('.runsrc\nruns.yml')
        subprocess.run(['git', 'add', '.gitignore'], cwd=self.work_dir)
        subprocess.run(['git', 'commit', '-qam', 'init'], cwd=self.work_dir)
        self.input_command = 'python -c "{}"'.format(
            """\
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--option', default=0)
print(vars(parser.parse_args()))\
""")
        self.description = 'test new command'

    def tearDown(self):
        shutil.rmtree(self.work_dir)

    @property
    def work_dir(self):
        return '/tmp/test-run-manager'

    @property
    def input_name(self):
        return 'test_run'

    @property
    def name(self):
        return self.input_name.split('/')[-1]


class TestNew(TestBase):
    def setUp(self):
        super().setUp()
        main.main(['new', self.input_name, self.input_command,
                   "--description=" + self.description, '-q'])

    @property
    def full_command(self):
        return self.input_command

    @property
    def db(self):
        with Path(self.work_dir, 'runs.yml').open() as f:
            return yaml.load(f)

    @property
    def db_entry(self):
        return get_name(self.db[CHILDREN], self.name)

    def tearDown(self):
        Run(self.input_name).kill_tmux()
        super().tearDown()

    def test_tmux(self):
        self.assertIn('"' + self.input_name + '"', sessions())

    def test_db(self):
        for key in ['commit', 'datetime']:
            with self.subTest(key=key):
                self.assertIn(key, self.db_entry)
        for key in ['description', 'full_command', 'name']:
            with self.subTest(key=key):
                self.assertEqual(self.db_entry[key], getattr(self, key))
        key = 'input_command'
        with self.subTest(key=key):
            self.assertEqual(self.db_entry[key], self.input_command)


class TestNewWithSubdir(TestNew):
    @property
    def db_entry(self):
        return get_name(get_name(self.db[CHILDREN], 'subdir')[CHILDREN], self.name)

    @property
    def input_name(self):
        return 'subdir/test_run'

    def test_db(self):
        self.assertEqual(self.db[CHILDREN][0][NAME], 'subdir')
        super().test_db()

    # def test_something(self):
    #     pprint(self.db)


class TestNewWithConfig(TestNew):
    def setUp(self):
        self.dir_names = ['checkpoints', 'tensorboard']
        self.root = '.runs'
        Path(self.work_dir, self.input_name).mkdir(parents=True)
        with Path(self.work_dir, '.runsrc').open('w') as f:
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
            path = Path(self.work_dir, self.root, dir_name, self.input_name)
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
        main.main(['rm', '-y', self.input_name])

    def test_tmux(self):
        self.assertNotIn('"' + self.input_name + '"', sessions())

    def test_rmdirs(self):
        for root, dirs, files in os.walk(self.work_dir):
            for file in files:
                with self.subTest(file=file):
                    self.assertNotEqual(self.input_name, file)


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
        self.assertEqual(Pattern('*').lookup('name'), [self.input_name])


class TestChdesc(TestNew):
    def test_chdescription(self):
        description = 'new description'
        main.main(['chdesc', self.input_name, '--description=' + description])
        self.assertEqual(Run(self.input_name).lookup('description'), description)
