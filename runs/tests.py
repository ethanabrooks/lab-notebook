import os
import shutil
import subprocess
from pathlib import Path
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


class TestNew(TestCase):
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
        main.main(['new', self.input_name, self.input_command,
                   "--description=" + self.description, '-q'])

    def tearDown(self):
        Run(self.input_name).kill_tmux()
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

    @property
    def full_command(self):
        return self.input_command

    @property
    def db(self):
        with Path(self.work_dir, 'runs.yml').open() as f:
            return yaml.load(f)

    @property
    def db_entry(self):
        self.assertIn(CHILDREN, self.db)
        return get_name(self.db[CHILDREN], self.name)

    @property
    def dir_names(self):
        return []

    @property
    def root(self):
        return '.runs'

    def test_tmux(self):
        self.assertIn('"' + self.input_name + '"', sessions())

    def test_db(self):
        for key in ['commit', 'datetime']:
            with self.subTest(key=key):
                self.assertIn(key, self.db_entry)
        for key in ['description', 'full_command', 'input_command', 'name']:
            with self.subTest(key=key):
                self.assertIn(key, self.db_entry)
                attr = self.input_command if key == 'input_command' else getattr(self, key)
                self.assertEqual(self.db_entry[key], attr)


class TestNewWithSubdir(TestNew):
    @property
    def db_entry(self):
        return get_name(get_name(self.db[CHILDREN], 'subdir')[CHILDREN], self.name)

    @property
    def input_name(self):
        return 'subdir/test_run'

    def test_db(self):
        self.assertIn('subdir', [child[NAME] for child in self.db[CHILDREN]])
        super().test_db()


class TestNewWithConfig(TestNew):
    def setUp(self):
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

    @property
    def full_command(self):
        return self.input_command + ' --option=1'

    @property
    def dir_names(self):
        return ['checkpoints', 'tensorboard']


class TestNewWithSubdirAndConfig(TestNewWithConfig, TestNewWithSubdir):
    pass


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


# class TestMove(TestNew):
#     def setUp(self):
#         super().setUp()
#         self.new_name = 'new_name'
#         main.main(['mv', '-y', '--keep-tmux', self.input_name, self.new_name])
