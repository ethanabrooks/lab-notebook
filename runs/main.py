#!/usr/bin/env python3
# stdlib
# stdlib
import argparse
import codecs
from configparser import ConfigParser, ExtendedInterpolation
from importlib import import_module
from pathlib import Path, PurePath
import pprint
import sys
from typing import List

# first party
from runs.logger import UI
from runs.subcommands import (build_spec, change_description, correlate, diff, kill, lookup, ls, mv, new,
                              new_from_spec, reproduce, rm)

MAIN = 'main'
ARGS = 'args'


def find_up(filename):
    dirpath = Path('.').resolve()
    while not dirpath.match(dirpath.root):
        filepath = Path(dirpath, filename)
        if filepath.exists():
            return filepath
        dirpath = dirpath.parent


def pure_path_list(paths: str) -> List[PurePath]:
    return [PurePath(path) for path in paths.split()]


def arg_list(args_string: str) -> List[List[str]]:
    return codecs.decode(args_string, encoding='unicode_escape').strip('\n').split('\n')


def main(argv=sys.argv[1:]):
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
        help='Custom path to directory where config directories (if any) are '
        'automatically '
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

    config = ConfigParser(
        delimiters=[':'],
        allow_no_value=True,
        interpolation=ExtendedInterpolation(),
        converters=dict(
            _path=Path,
            _pure_path=PurePath,
            _pure_path_list=pure_path_list,
            _arg_list=arg_list))
    config_filename = Path('.runsrc')
    config_path = find_up(config_filename)
    missing_config_keys = []
    default_values = dict(
        root=str(Path('.runs').absolute()),
        db_path=str(Path('runs.db').absolute()),
        dir_names=[],
        args=[])
    if config_path:
        config.read(str(config_path))

    if MAIN not in config:
        config[MAIN] = {}

    for k, v in default_values.items():
        if k not in config[MAIN]:
            missing_config_keys.append(k)
            config[MAIN][k] = v

    main_config = dict(
        root=config[MAIN].get_path('root'),
        db_path=config[MAIN].get_path('db_path'),
        dir_names=config[MAIN].get_pure_path_list('dir_names'),
        args=(config[MAIN].get_arg_list(ARGS)))

    for subparser in [parser] + [
            adder(subparsers) for adder in [
                new.add_subparser,
                new_from_spec.add_subparser,
                rm.add_subparser,
                mv.add_subparser,
                ls.add_subparser,
                lookup.add_subparser,
                change_description.add_subparser,
                reproduce.add_subparser,
                correlate.add_subparser,
                kill.add_subparser,
                diff.add_subparser,
                build_spec.add_subparser,
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
    ui = UI(assume_yes=args.assume_yes, quiet=args.quiet)

    def write_config():
        if ui.get_permission(f'Write new config to {config_filename.absolute()}?'):
            with config_filename.open('w') as f:
                config.write(f)
        else:
            ui.exit()

    if not config_path:
        ui.print(
            'Config not found. Using default config:',
            pprint.pformat(dict(config[MAIN])),
            sep='\n')
        write_config()
    elif missing_config_keys:
        for key in missing_config_keys:
            ui.print(f'Using default value for {key}: {main_config[key]}')
        write_config()

    module = import_module('runs.subcommands.' + args.dest.replace('-', '_'))
    kwargs = {k: v for k, v in vars(args).items()}
    try:
        # pluralize args
        kwargs[ARGS] = list(set(args.arg) | set(main_config[ARGS]))
    except AttributeError:
        pass

    module.cli(**kwargs)


if __name__ == '__main__':
    main()
