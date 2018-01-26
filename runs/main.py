#!/usr/bin/env python3
import argparse
import os

import yaml

from runs.commands import new, bulk_move, delete, lookup, reproduce, load_table, move
from runs.util import load, find_file_backward, split_pattern, Config, NAME, PATTERN, \
    NEW, DELETE, MOVE, LOOKUP, LIST, TABLE, REPRODUCE, collect_runs


def main():
    runsrc_file = find_file_backward('.runsrc')
    if runsrc_file is None:
        cfg = Config(root='.')
    else:
        cfg = Config(root=os.path.dirname(runsrc_file))
        # load values from config
        with open(runsrc_file) as f:
            print('Config file loaded.')
            for k, v in yaml.load(f).items():

                # Don't treat None like a string
                if v in ['None', 'True', 'False']:
                    v = eval(v)

                cfg.setattr(k, v)

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=None,
                        help='IP address or hostname (without username). Used for accessing '
                             'database on remote server.')
    parser.add_argument('--username', default=None,
                        help='Username associated with remote host. Used for accessing '
                             'database on remote server.')
    parser.add_argument('--runs_dir', default=cfg.runs_dir, help='Custom path to directory containing runs '
                                                                    'database (default, `runs.yml`). Should not '
                                                                    'need to be specified for local runs but '
                                                                    'probably required for accessing databses '
                                                                    'remotely.')
    parser.add_argument('--db_filename', default=cfg.db_filename,
                        help='Name of YAML file storing run database information.')

    subparsers = parser.add_subparsers(dest='dest')

    virtualenv_path_help = 'Path to virtual environment, if one is being ' \
                           'used. If not `None`, the program will source ' \
                           '`<virtualenv-path>/bin/activate`.'

    path_clarification = ' Can be a relative path from runs: `DIR/NAME|PATTERN` Can also be a pattern. '

    new_parser = subparsers.add_parser(NEW, help='Start a new run.')
    new_parser.add_argument(NAME, help='Unique name assigned to new run.' + path_clarification)
    new_parser.add_argument('command', help='Command to run to start tensorflow program. Do not include the `--tb-dir` '
                                            'or `--save-path` flag in this argument')
    new_parser.add_argument('--tb-dir-flag', default=cfg.tb_dir_flag,
                            help='Flag to pass to program to specify tensorboard '
                                 'directory.')
    new_parser.add_argument('--save-path-flag', default=cfg.save_path_flag,
                            help='Flag to pass to program to specify '
                                 'tensorboard directory.')
    new_parser.add_argument('--virtualenv-path', default=None, help=virtualenv_path_help)
    new_parser.add_argument('--no-overwrite', action='store_true', help='If this flag is given, a timestamp will be '
                                                                        'appended to any new name that is already in '
                                                                        'the database.  Otherwise this entry will '
                                                                        'overwrite any entry with the same name. ')
    new_parser.add_argument('--description', help='Description of this run. Write whatever you want.')

    delete_parser = subparsers.add_parser(DELETE,
                                          help="Delete runs from the database (and all associated tensorboard "
                                               "and checkpoint files). Don't worry, the script will ask for "
                                               "confirmation before deleting anything.")
    delete_parser.add_argument(PATTERN,
                               help='This script will only delete entries in the database whose names are a '
                                    'complete (not partial) match of this regex pattern.')

    move_parser = subparsers.add_parser(MOVE, help='Move a run from OLD to NEW.')
    move_parser.add_argument('old', help='Name of run to rename.' + path_clarification)
    move_parser.add_argument('new', help='New name for run.' + path_clarification)
    move_parser.add_argument('--' + PATTERN, action='store_true',
                             help='Whether to do a bulk move, interpreting OLD as a pattern')
    move_parser.add_argument('--kill-tmux', action='store_true',
                             help='Kill tmux after the move.')

    pattern_help = 'Only display names matching this pattern.'
    list_parser = subparsers.add_parser(LIST, help='List all names in run database.')
    list_parser.add_argument(PATTERN, nargs='?', default=None, help=pattern_help)

    table_parser = subparsers.add_parser(TABLE, help='Display contents of run database as a table.')
    table_parser.add_argument(PATTERN, nargs='?', default=None, help=pattern_help)
    table_parser.add_argument('--hidden-columns', default='input-command',
                              help='Comma-separated list of columns to not display in table.')
    table_parser.add_argument('--column-width', type=int, default=cfg.column_width,
                              help='Maximum width of table columns. Longer values will '
                                   'be truncated and appended with "...".')

    lookup_parser = subparsers.add_parser(LOOKUP, help='Lookup specific value associated with database entry')
    lookup_parser.add_argument(NAME, help='Name of run that value is associated with.')
    lookup_parser.add_argument('key', help='Key that value is associated with. To view all available keys, '
                                           'use `--key=None`.')

    reproduce_parser = subparsers.add_parser(
        REPRODUCE, help='Print commands to reproduce a run.')
    reproduce_parser.add_argument(NAME)
    reproduce_parser.add_argument('--description', type=str, default=None, help='Description to be assigned to new '
                                                                                'run. If None, use the same '
                                                                                'description as the run being '
                                                                                'reproduced.')
    reproduce_parser.add_argument('--virtualenv-path', default=None, help=virtualenv_path_help)
    reproduce_parser.add_argument('--no-overwrite', action='store_true',
                                  help='If this flag is given, a timestamp will be '
                                       'appended to any new name that is already in '
                                       'the database.  Otherwise this entry will '
                                       'overwrite any entry with the same name. ')

    args = parser.parse_args()

    for k, v in vars(args).items():
        if v is not None:  # None indicates that the flag was not set by the user.
            cfg.setattr(k, v)

    if args.dest == NEW:
        runs_dir, name = split_pattern(args.runs_dir, args.name)
        assert args.host is None, 'SSH into remote before calling runs new.'
        new(name=name,
            description=args.description,
            virtualenv_path=cfg.virtualenv_path,
            command=args.command,
            overwrite=not args.no_overwrite,
            runs_dir=runs_dir,
            db_filename=cfg.db_filename,
            tb_dir_flag=cfg.tb_dir_flag,
            save_path_flag=cfg.save_path_flag,
            extra_flags=cfg.extra_flags)

    elif args.dest == DELETE:
        runs_dir, run_names = collect_runs(args.runs_dir, args.pattern,
                                           cfg.db_filename, cfg.regex)
        assert args.host is None, 'SSH into remote before calling runs delete.'
        delete(run_names, cfg.db_filename, runs_dir)

    elif args.dest == MOVE:
        old_runs_dir, old_run_names = collect_runs(args.runs_dir, args.old,
                                                   cfg.db_filename, cfg.regex)
        new_runs_dir, new_pattern = split_pattern(args.runs_dir, args.new)
        if len(old_run_names) > 1:
            bulk_move(old_run_names, old_runs_dir, new_runs_dir,
                      cfg.db_filename, args.kill_tmux)
        else:
            move(old_runs_dir, old_run_names[0], new_runs_dir, new_pattern,
                 cfg.db_filename, args.kill_tmux)

    elif args.dest == LIST:
        _, names = collect_runs(args.runs_dir, args.pattern, cfg.db_filename, cfg.regex)
        for name in names:
            print(name)

    elif args.dest == TABLE:
        hidden_columns = args.hidden_columns.split(',')
        runs_dir, run_names = collect_runs(cfg.runs_dir, args.pattern,
                                           cfg.db_filename, cfg.regex)
        print(load_table(runs_dir=runs_dir,
                         db_filename=cfg.db_filename,
                         run_names=run_names,
                         host=args.host,
                         column_width=cfg.column_width,
                         username=args.username,
                         hidden_columns=hidden_columns))

    elif args.dest == LOOKUP:
        runs_dir, pattern = split_pattern(args.runs_dir, args.name)
        db = load(os.path.join(runs_dir, cfg.db_filename))
        print(lookup(db, args.name, args.key))

    elif args.dest == REPRODUCE:
        reproduce(cfg.runs_dir, cfg.db_filename, args.name)

    else:
        raise RuntimeError("'{}' is not a supported dest.".format(args.dest))


if __name__ == '__main__':
    main()
