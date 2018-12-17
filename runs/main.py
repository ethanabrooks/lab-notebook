#!/usr/bin/env python3
# stdlib
# stdlib
import argparse
import codecs
from configparser import ConfigParser, ExtendedInterpolation
from importlib import import_module
from pathlib import Path, PurePath
import sys
from typing import List

# first party
from runs.commands import (change_description, correlate, flags, kill, lookup, ls, mv,
                           new, new_from_spec, reproduce, rm)
from runs.logger import Logger

MAIN = 'main'
FLAGS = 'flags'


def find_up(filename):
    dirpath = Path('.').resolve()
    while not dirpath.match(dirpath.root):
        filepath = Path(dirpath, filename)
        if filepath.exists():
            return filepath
        dirpath = dirpath.parent


def pure_path_list(paths: str) -> List[PurePath]:
    return [PurePath(path) for path in paths.split()]


def flag_list(flags_string: str) -> List[List[str]]:
    return codecs.decode(flags_string, encoding='unicode_escape').strip('\n').split('\n')


def main(argv=sys.argv[1:]):
    config = ConfigParser(
        delimiters=[':'],
        allow_no_value=True,
        interpolation=ExtendedInterpolation(),
        converters=dict(
            _path=Path,
            _pure_path=PurePath,
            _pure_path_list=pure_path_list,
            _flag_list=flag_list))
    config_filename = '.runsrc'
    config_path = find_up(config_filename)
    if config_path:
        config.read(str(config_path))
    else:
        config[MAIN] = dict(
            root=Path('.runs').absolute(),
            db_path=Path('runs.db').absolute(),
        )

    parser = argparse.ArgumentParser(
        epilog="The script will ask permission before running, deleting, moving, or "
        "permanently changing anything.")
    parser.add_argument(
        '--quiet', '-q', action='store_true', help='Suppress print output')
    parser.add_argument(
        '--db-path',
        help='path to sqlite file storing run database information.',
        type=Path)
    parser.add_argument(
        '--root',
        help='Custom path to directory where config directories (if any) are automatically '
        'created',
        type=Path)
    parser.add_argument(
        '--dir-names',
        type=pure_path_list,
        help="directories to create and sync automatically with each run")
    parser.add_argument(
        '--assume-yes',
        '-y',
        action='store_true',
        help='Don\'t ask permission before performing operations.')

    subparsers = parser.add_subparsers(dest='dest')

    main_config = dict(config[MAIN])
    main_config.update(
        root=config[MAIN].get_path('root'),
        db_path=config[MAIN].get_path('db_path'),
        dir_names=config[MAIN].get_pure_path_list('dir_names', []),
        flags=(config[MAIN].get_flag_list(FLAGS, [])))

    for subparser in [parser] + [
            adder(subparsers) for adder in [
                new.add_subparser,
                new_from_spec.add_subparser,
                rm.add_subparser,
                mv.add_subparser,
                ls.add_subparser,
                lookup.add_subparser,
                flags.add_subparser,
                change_description.add_subparser,
                reproduce.add_subparser,
                correlate.add_subparser,
                kill.add_subparser,
            ]
    ]:
        assert isinstance(subparser, argparse.ArgumentParser)
        config_section = subparser.prog.split()[-1]
        assert isinstance(config_section, str)
        subparser.set_defaults(**config['DEFAULT'])
        subparser.set_defaults(**main_config)
        if config_section in config:
            subparser.set_defaults(**config[config_section])

    args = parser.parse_args(args=argv)

    logger = Logger(quiet=args.quiet)
    if not config_path:
        logger.print('Config file not found. Using default settings:\n')
        for section in config.sections():
            for k, v in config[section].items():
                logger.print('{:20}{}'.format(k + ':', v))
        logger.print()
        msg = 'Writing default settings to ' + config_filename
        logger.print(msg)
        logger.print('-' * len(msg))

    with open(config_filename, 'w') as f:
        config.write(f)

    module = import_module('runs.commands.' + args.dest.replace('-', '_'))
    kwargs = {k: v for k, v in vars(args).items()}
    try:
        # pluralize flags
        kwargs[FLAGS] = list(set(args.flag) | set(main_config[FLAGS]))
    except AttributeError:
        pass
    module.cli(**kwargs)


if __name__ == '__main__':
    main()
