#!/usr/bin/env python3
import argparse
import shutil
import sys
from configparser import ConfigParser, ExtendedInterpolation
from pathlib import Path

from runs.db import RunEntry, Table
from runs.run import Run, move
from runs.util import (CHDESCRIPTION, DEFAULT, KILLALL, LIST, LOOKUP, MAIN,
                       MOVE, NEW, PATH, PATTERN, REMOVE, REPRODUCE, TABLE,
                       _exit, get_permission, search_ancestors)


def nonempty_string(value):
    if value == '' or not isinstance(value, str):
        raise argparse.ArgumentTypeError("Value must be a nonempty string.")
    return value


def main(argv=sys.argv[1:]):
    config = ConfigParser(
        delimiters=[':'],
        allow_no_value=True,
        interpolation=ExtendedInterpolation())
    config_filename = '.runsrc'
    config_path = search_ancestors(config_filename)
    if config_path:
        config.read(str(config_path))
    else:
        config[MAIN] = {
            # Custom path to directory containing runs database (default, `runs.db`). Should not need to be
            # specified for local runs but probably required for accessing databses remotely.
            'root': Path('.runs').absolute(),

            # path to YAML file storing run database information.
            'db_path': Path('runs.db').absolute(),

            # directories that runs should create
            'dir_names': '',
            'prefix': '',
        }
        config['flags'] = {}

        print('Config file not found. Using default settings:\n')
        for section in config.sections():
            for k, v in config[section].items():
                print('{:20}{}'.format(k + ':', v))
        print()
        msg = 'Writing default settings to ' + config_filename
        print(msg)
        print('-' * len(msg))

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
        type=Path)
    parser.add_argument(
        '--prefix',
        type=str,
        help=
        "String to preprend to all main commands, for example, sourcing a virtualenv"
    )
    parser.add_argument(
        '--dir-names',
        type=str,
        help="directories to create and sync automatically with each run")
    parser.add_argument(
        '--quiet', '-q', action='store_true', help='Suppress print output')
    parser.add_argument(
        '--assume-yes',
        '-y',
        action='store_true',
        help='Don\'t ask permission before performing operations.')
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
    set_defaults(remove_parser, REMOVE)

    move_parser = subparsers.add_parser(
        MOVE,
        help='Move a run from OLD to NEW. '
        'Functionality is identical to `mkdir -p` except that non-existent dirs'
        'are created and empty dirs are removed automatically'
        'The program will show you planned '
        'moves and ask permission before changing anything.')
    move_parser.add_argument(
        'source',
        help='Name of run to rename.' + path_clarification,
        type=nonempty_string)
    move_parser.add_argument(
        'destination',
        help='New name for run.' + path_clarification,
        type=nonempty_string)
    move_parser.add_argument(
        '--kill-tmux',
        action='store_true',
        help='Kill tmux session instead of renaming it.')
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

    with Table(args.db_path) as table:

        if hasattr(args, 'path'):

            run = Run(
                path=args.path,
                table=table,
                root=args.root,
                dir_names=args.dir_names,
                quiet=args.quiet)

            if args.dest == NEW:
                run.new(
                    prefix=args.prefix,
                    command=args.command,
                    description=args.description,
                    assume_yes=args.assume_yes,
                    flags=list(config['flags']))

            elif args.dest == CHDESCRIPTION:
                run.chdescription(args.description)

            elif args.dest == REPRODUCE:
                print(run.reproduce())
        else:
            if hasattr(args, 'pattern'):
                pattern = args.pattern if args.pattern else '%'
            else:
                pattern = '%'

            runs = [
                Run(path=run.path,
                    table=table,
                    root=args.root,
                    dir_names=args.dir_names,
                    quiet=args.quiet) for run in table[pattern]
            ]
            run_paths = [str(run.path) for run in runs]

            if args.dest == REMOVE:
                prompt = 'Runs to be removed:\n{}\nContinue?'.format(
                    '\n'.join(run_paths))
                if args.assume_yes or get_permission(prompt):
                    for run in runs:
                        run.remove()

            elif args.dest == LIST:
                # TODO: again, None patterns should be converted to '.' inside the class
                # pattern = args.pattern if args.pattern else Pattern('.')
                if args.porcelain:
                    for run in runs:
                        print(run.path)
                else:
                    for run in runs:
                        print(run.path)

            elif args.dest == TABLE:
                raise NotImplemented

            elif args.dest == LOOKUP:
                for run in table[pattern]:
                    try:
                        print(getattr(run, args.key))
                    except AttributeError:
                        # noinspection PyProtectedMember
                        _exit(
                            f"{args.key} is not a valid key. Valid keys are: {RunEntry.fields()}."
                        )

            elif args.dest == MOVE:
                # TODO: this kind of validation should occur within the classes
                # if not RunsPath(args.old).runs():
                #     no_match(args.old, db_path=DBPath.cfg.db_path)
                move(
                    src_pattern=args.source,
                    dest_path=args.destination,
                    table=table,
                    kill_tmux=args.kill_tmux,
                    assume_yes=args.assume_yes,
                    root=args.root,
                    dir_names=args.dir_names,
                    quiet=args.quiet)

                # if args.summary_path:
                #     from runs.tensorflow_util import summarize_run
                #     path = summarize_run(args.path, args.summary_path)
                #     print('\nWrote summary to', path)

            elif args.dest == KILLALL:
                run_paths = '\n'.join(run_paths)
                if get_permission(
                        f"Runs to be removed:\n{run_paths}\nContinue?"):
                    for run in runs:
                        print(run.path)
                    table.delete()
                    args.db_path.unlink()
                    shutil.rmtree(str(args.root), ignore_errors=True)

            else:
                raise RuntimeError("'{}' is not a supported dest.".format(
                    args.dest))


if __name__ == '__main__':
    main()
