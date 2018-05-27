#!/usr/bin/env python3
import argparse
import inspect
import itertools
import os
import sys
from configparser import ConfigParser, ExtendedInterpolation

from runs.config import Config
from runs.db import killall, no_match
from runs.pattern import Pattern
from runs.runs_path import RunsPath
from runs.run import Run
from runs.util import (CHDESCRIPTION, DEFAULT, FLAGS, KILLALL, LIST, LOOKUP,
                       MAIN, MOVE, NEW, PATH, PATTERN, REMOVE, REPRODUCE,
                       TABLE, cmd, search_ancestors, ROOT_PATH)


def nonempty_string(value):
    if value == '' or not isinstance(value, str):
        raise argparse.ArgumentTypeError("Value must be a nonempty string.")
    return value


def main(argv=sys.argv[1:]):
    config = ConfigParser(
        allow_no_value=True, interpolation=ExtendedInterpolation())
    config_filename = '.runsrc'
    config_path = search_ancestors(config_filename)
    config[MAIN] = {
        # Custom path to directory containing runs database (default, `runs.pkl`). Should not need to be
        # specified for local runs but probably required for accessing databses remotely.
        'root': os.getcwd() + '/.runs',

        # path to YAML file storing run database information.
        'db_path': os.getcwd() + '/runs.pkl',

        # directories that runs should create
        'dir_names': None,
        'prefix': None,
    }
    if config_path:
        config.read(str(config_path))
    else:
        with open(config_filename, 'w') as f:
            config.write(f)

    def set_defaults(parser, name):
        assert isinstance(parser, argparse.ArgumentParser)
        assert isinstance(name, str)

        parser.set_defaults(**config[DEFAULT])
        if name in config:
            parser.set_defaults(**config[name])

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--root',
        help=
        'Custom path to directory where config directories (if any) are automatically '
        'created',
        type=nonempty_string)
    parser.add_argument(
        '--db-path',
        help='path to YAML file storing run database information.',
        type=nonempty_string)
    parser.add_argument(
        '--prefix',
        type=nonempty_string,
        help="String to preprend to all main commands, for example, sourcing a virtualenv")
    parser.add_argument(
        '--quiet', '-q', action='store_true', help='Suppress print output')
    set_defaults(parser, MAIN)

    subparsers = parser.add_subparsers(dest='dest')
    path_clarification = ' Can be a relative path from runs: `DIR/NAME|PATTERN` Can also be a pattern. '

    new_parser = subparsers.add_parser(NEW, help='Start a new run.')
    new_parser.add_argument(
        PATH,
        help='Unique path assigned to new run. "\\"-delimited.',
        type=nonempty_string)
    new_parser.add_argument(
        'command',
        help='Command that will be run in tmux.',
        type=nonempty_string)
    new_parser.add_argument(
        '--assume-yes',
        '-y',
        action='store_true',
        help='Don\'t ask permission before overwriting '
        'existing entries.')
    new_parser.add_argument(
        '--description',
        help='Description of this run. Explain what this run was all about or '
        'just write whatever your heart desires. If this argument is `commit-message`,'
        'it will simply use the last commit message.')
    new_parser.add_argument(
        '--summary-path',
        help='Path where Tensorflow summary of run is to be written.')
    set_defaults(new_parser, NEW)

    remove_parser = subparsers.add_parser(
        REMOVE,
        help="Delete runs from the database (and all associated tensorboard "
        "and checkpoint files). Don't worry, the script will ask for "
        "confirmation before deleting anything.")
    remove_parser.add_argument(
        PATTERN,
        help=
        'This script will only delete entries in the database whose names are a complete '
        '(not partial) match of this glob pattern.',
        type=nonempty_string)
    remove_parser.add_argument(
        '--assume-yes',
        '-y',
        action='store_true',
        help='Don\'t request permission from user before deleting.')
    set_defaults(remove_parser, REMOVE)

    move_parser = subparsers.add_parser(
        MOVE,
        help='Move a run from OLD to NEW. The program will show you planned '
        'moves and ask permission before changing anything')
    move_parser.add_argument(
        'old',
        help='Name of run to rename.' + path_clarification,
        type=nonempty_string)
    move_parser.add_argument(
        'new',
        help='New name for run.' + path_clarification,
        type=nonempty_string)
    move_parser.add_argument(
        '--kill-tmux',
        action='store_true',
        help='Kill tmux session instead of renaming it.')
    move_parser.add_argument(
        '--assume-yes',
        '-y',
        action='store_true',
        help='Don\'t request permission from user before moving.')
    set_defaults(move_parser, MOVE)

    pattern_help = 'Only display paths matching this pattern.'

    list_parser = subparsers.add_parser(
        LIST, help='List all names in run database.')
    list_parser.add_argument(
        PATTERN, nargs='?', help=pattern_help, type=nonempty_string)
    list_parser.add_argument(
        '--show-attrs',
        action='store_true',
        help='Print run attributes in addition to names.')
    list_parser.add_argument(
        '--porcelain',
        action='store_true',
        help='Print list of path names without tree '
        'formatting.')
    set_defaults(list_parser, LIST)

    table_parser = subparsers.add_parser(
        TABLE, help='Display contents of run database as a table.')
    table_parser.add_argument(
        PATTERN,
        nargs='?',
        default='*',
        help=pattern_help,
        type=nonempty_string)
    table_parser.add_argument(
        '--hidden-columns',
        help='Comma-separated list of columns to not display in table.')
    table_parser.add_argument(
        '--column-width',
        type=int,
        default=100,
        help='Maximum width of table columns. Longer values will '
        'be truncated and appended with "...".')
    set_defaults(table_parser, TABLE)

    lookup_parser = subparsers.add_parser(
        LOOKUP, help='Lookup specific value associated with database entry')
    lookup_parser.add_argument(
        'key', help='Key that value is associated with.')
    lookup_parser.add_argument(
        PATTERN,
        help='Pattern of runs for which to retrieve key.',
        type=nonempty_string)
    set_defaults(lookup_parser, LOOKUP)

    chdesc_parser = subparsers.add_parser(
        CHDESCRIPTION, help='Edit description of run.')
    chdesc_parser.add_argument(
        PATH,
        help='Name of run whose description you want to edit.',
        type=nonempty_string)
    chdesc_parser.add_argument(
        '--description',
        default=None,
        help='New description. If None, script will prompt for '
        'a description in Vim')
    set_defaults(chdesc_parser, CHDESCRIPTION)

    reproduce_parser = subparsers.add_parser(
        REPRODUCE,
        help='Print commands to reproduce a run. This command '
        'does not have side-effects (besides printing).')
    reproduce_parser.add_argument(PATH)
    reproduce_parser.add_argument(
        '--description',
        type=nonempty_string,
        default=None,
        help=
        "Description to be assigned to new run. If None, use the same description as "
        "the run being reproduced.")
    reproduce_parser.add_argument(
        '--no-overwrite',
        action='store_true',
        help='If this flag is given, a timestamp will be '
        'appended to any new name that is already in '
        'the database.  Otherwise this entry will '
        'overwrite any entry with the same name. ')
    set_defaults(reproduce_parser, REPRODUCE)

    subparsers.add_parser(KILLALL, help='Destroy all runs.')
    args = parser.parse_args(args=argv)

    kwargs = {
        k: v
        for k, v in vars(args).items()
        if k in inspect.signature(Config).parameters
    }
    # kwargs[FLAGS] = {
    #     k + '=' + v if v else k
    #     for k, v in (config[FLAGS].items() if FLAGS in config else {})
    # }

    # if hasattr(args, PATTERN):
    #     if args.pattern and not Pattern(args.pattern).runs():
    #         no_match(args.pattern, db_path=DBPath.cfg.db_path)

    if config_path is None:
        print('Config file not found. Using default settings:\n')
        for k, v in config[DEFAULT].items():
            print('{:20}{}'.format(k + ':', v))
        print()
        msg = 'Writing default settings to ' + config_filename
        print(msg)
        print('-' * len(msg))

    cfg = Config(**kwargs)
    root = RootNode(cfg.root_path)

    if args.dest == KILLALL:
        print('Remove current runs?')
        with root.open('w') as r:
            RunsPath('.', root=r, cfg=cfg).rmdirs()

    elif args.dest == NEW:
        with root.open('w') as r:
            for path, flags in cfg.generate_runs(args.path):
                Run(path, root, cfg).new(
                    command=args.command,
                    description=args.description,
                    assume_yes=args.assume_yes,
                    flags=flags)

            # if args.summary_path:
            #     from runs.tensorflow_util import summarize_run
            #     path = summarize_run(args.path, args.summary_path)
            #     print('\nWrote summary to', path)

    elif args.dest == REMOVE:
        with root.open('w') as r:
            RunsPath(args.pattern, r, cfg).rmdirs(args.assume_yes)

    elif args.dest == MOVE:
        with root.open('w') as r:
            # TODO: this kind of validation should occur within the classes
            # if not RunsPath(args.old).runs():
            #     no_match(args.old, db_path=DBPath.cfg.db_path)
            RunsPath(args.old, r, cfg).move(
                dest=RunsPath(args.new),
                kill_tmux=args.kill_tmux,
                assume_yes=args.assume_yes)

    elif args.dest == LIST:
        # TODO: again, None patterns should be converted to '.' inside the class
        # pattern = args.pattern if args.pattern else Pattern('.')
        with root.open('r') as r:
            RunsPath(args.pattern, r, cfg).pretty_print(args.porcelain, args.show_attrs)

    elif args.dest == TABLE:
        with root.open('r') as r:
            RunsPath(args.pattern, r, cfg).pretty_print(args.porcelain, args.show_attrs)
            print(Pattern(args.pattern).table(args.column_width))

    elif args.dest == LOOKUP:
        pattern = Pattern(args.pattern)
        runs = pattern.runs()
        # TODO: Pattern should handle this kind of logic
        if len(runs) == 1:
            print(pattern.lookup(args.key)[0])
        else:
            for run, value in zip(runs, pattern.lookup(args.key)):
                print("{}: {}".format(run.path, value))

    elif args.dest == CHDESCRIPTION:
        # TODO: Run should check whether things exist
        Run(args.path).chdescription(args.description)

    elif args.dest == REPRODUCE:
        print(Run(args.path).reproduce())

    else:
        raise RuntimeError("'{}' is not a supported dest.".format(args.dest))


if __name__ == '__main__':
    main()
