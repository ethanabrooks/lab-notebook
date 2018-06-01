#!/usr/bin/env python3
import argparse
import sys
from configparser import ConfigParser, ExtendedInterpolation
from importlib import import_module
from pathlib import Path
from pprint import pprint

from runs import commands
from runs.commands import (change_description, killall, lookup, ls, mv, new,
                           reproduce, rm, table)
from runs.commands.change_description import add_subparser
from runs.commands.killall import add_subparser
from runs.commands.lookup import add_subparser
from runs.commands.ls import add_subparser
from runs.commands.mv import add_subparser
from runs.commands.new import add_subparser
from runs.commands.reproduce import add_subparser
from runs.commands.rm import add_subparser
from runs.commands.table import add_subparser
from runs.util import DEFAULT, MAIN, find_up, nonempty_string


def main(argv=sys.argv[1:]):
    config = ConfigParser(
        delimiters=[':'], allow_no_value=True, interpolation=ExtendedInterpolation())
    config_filename = '.runsrc'
    config_path = find_up(config_filename)
    if config_path:
        config.read(str(config_path))
    else:
        config[MAIN] = dict(
            root=Path('.runs').absolute(),
            db_path=Path('runs.db').absolute(),
            dir_names='',
            prefix='',
            flags='',
        )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--quiet', '-q', action='store_true', help='Suppress print output')
    parser.add_argument(
        '--db-path',
        help='path to YAML file storing run database information.',
        type=Path)
    parser.add_argument(
        '--root',
        help='Custom path to directory where config directories (if any) are automatically '
        'created',
        type=nonempty_string)
    parser.add_argument(
        '--dir-names',
        type=str,
        help="directories to create and sync automatically with each run")
    parser.add_argument(
        '--assume-yes',
        '-y',
        action='store_true',
        help='Don\'t ask permission before performing operations.')

    subparsers = parser.add_subparsers(dest='dest')

    for subparser in [parser] + [
            adder(subparsers) for adder in [
                new.add_subparser,
                rm.add_subparser,
                mv.add_subparser,
                ls.add_subparser,
                table.add_subparser,
                lookup.add_subparser,
                change_description.add_subparser,
                reproduce.add_subparser,
                killall.add_subparser,
            ]
    ]:
        assert isinstance(subparser, argparse.ArgumentParser)
        config_section = subparser.prog.split()[-1]
        assert isinstance(config_section, str)
        subparser.set_defaults(**config[DEFAULT])
        subparser.set_defaults(**config[MAIN])
        if config_section in config:
            subparser.set_defaults(**config[config_section])

    args = parser.parse_args(args=argv)
    if args.flags != config[MAIN]['flags']:
        args.flags += '\n' + config[MAIN]['flags']

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
    module.cli(**kwargs)


if __name__ == '__main__':
    main()
