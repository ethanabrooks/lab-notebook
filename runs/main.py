#!/usr/bin/env python3
import argparse
import inspect
import os
import pprint
import sys
from configparser import ConfigParser, ExtendedInterpolation
from importlib import import_module
from pathlib import Path

from runs.commands.change_description import add_chdesc_parser
from runs.commands.killall import add_killall_parser
from runs.commands.lookup import add_lookup_parser
from runs.commands.ls import add_list_parser
from runs.commands.mv import add_move_parser
from runs.commands.new import add_new_parser
from runs.commands.remove import add_remove_parser
from runs.util import (DEFAULT, KILLALL, MAIN,
                       PATH, PATTERN, REPRODUCE, TABLE,
                       findup, nonempty_string)


def main(argv=sys.argv[1:]):
    config = ConfigParser(
        delimiters=[':'],
        allow_no_value=True,
        interpolation=ExtendedInterpolation())
    config_filename = '.runsrc'
    config_path = findup(config_filename)
    if config_path:
        config.read(str(config_path))
    else:
        config[MAIN] = dict(
            root=Path('.runs').absolute(),
            db_path=Path('runs.db').absolute(),
            dir_names='',
            prefix='',
        )
        config['flags'] = dict()

    # TODO can we improve this?
    def set_defaults(parser: argparse.ArgumentParser):
        assert isinstance(parser, argparse.ArgumentParser)
        name = parser.prog.split()[-1]
        assert isinstance(name, str)
        parser.set_defaults(**config[DEFAULT])
        parser.set_defaults(**config[MAIN])
        if name in config:
            parser.set_defaults(**config[name])

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--db-path',
        help='path to YAML file storing run database information.',
        type=Path)
    parser.add_argument(
        '--quiet', '-q', action='store_true', help='Suppress print output')
    set_defaults(parser)

    subparsers = parser.add_subparsers(dest='dest')
    path_clarification = ' Can be a relative path from runs: `DIR/NAME|PATTERN` Can also be a pattern. '

    new_parser = add_new_parser(subparsers)
    set_defaults(new_parser)

    remove_parser = add_remove_parser(subparsers)
    set_defaults(remove_parser)

    move_parser = add_move_parser(path_clarification, subparsers)
    set_defaults(move_parser)

    pattern_help = 'Only display paths matching this pattern.'

    list_parser = add_list_parser(pattern_help, subparsers)
    set_defaults(list_parser)

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
    set_defaults(table_parser)

    lookup_parser = add_lookup_parser(subparsers)
    set_defaults(lookup_parser)

    chdesc_parser = add_chdesc_parser(subparsers)
    set_defaults(chdesc_parser)

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
    set_defaults(reproduce_parser)
    killall_parser = add_killall_parser(subparsers)
    set_defaults(killall_parser)

    args = parser.parse_args(args=argv)

    # TODO: use Logger
    def _print(*s):
        if not args.quiet:
            print(*s)

    if not config_path:
        _print('Config file not found. Using default settings:\n')
        for section in config.sections():
            for k, v in config[section].items():
                _print('{:20}{}'.format(k + ':', v))
        _print()
        msg = 'Writing default settings to ' + config_filename
        _print(msg)
        _print('-' * len(msg))

    with open(config_filename, 'w') as f:
        config.write(f)

    module = import_module('runs.commands.' + args.dest.replace('-', '_'))
    kwargs = {k: v for k, v in vars(args).items()}
    pprint.pprint(kwargs)
    module.cli(**kwargs)


if __name__ == '__main__':
    main()
