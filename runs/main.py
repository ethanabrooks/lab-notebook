#!/usr/bin/env python3
import argparse
from configparser import ConfigParser

import sys

import subprocess

from runs.cfg import Cfg
from runs.pattern import Pattern
from runs.run import Run
from runs.db_path import DBPath
from runs.util import search_ancestors, NAME, PATTERN, \
    NEW, REMOVE, MOVE, LOOKUP, LIST, TABLE, REPRODUCE, CHDESCRIPTION, print_tree


# conf_parser = argparse.ArgumentParser(
#     description=__doc__,  # printed with -h/--help
#     # Don't mess with format of description
#     formatter_class=argparse.RawDescriptionHelpFormatter,
#     # Turn off help, so we print all options in response to -h
#     add_help=False
# )
# defaults = dict(
#     db_path='runs.yml',
#     root_dir=Path(runsrc_path.parent, '.runs'),
#     dir_names=[],
# )
#
#     defaults.update(dict(config))
#
# parser = argparse.ArgumentParser(
#     # Inherit options from config_parser
#     parents=[conf_parser]
# )
#
# parser.set_defaults(**defaults)

# if runsrc_path is None:
#     cfg = Config(root=Path.cwd())
# else:
#     assert isinstance(runsrc_path, Path)
#     cfg = Config(root=runsrc_path.parent)
#     # load values from config
#     with runsrc_path.open() as f:
#         for k, v in yaml.load(f).items():
#             cfg.setattr(k, v)


def main(argv=sys.argv[1:]):
    config = ConfigParser(allow_no_value=True)
    config_filename = '.runsrc'
    config_path = search_ancestors(config_filename)
    if config_path:
        config.read(config_path)
    else:
        config['DEFAULT'] = {
            # Custom path to directory containing runs database (default, `runs.yml`). Should not need to be
            # specified for local runs but probably required for accessing databses remotely.
            'root': '.runs',

            # path to YAML file storing run database information.
            'db_path': 'runs.yml',

            # directories that runs should create
            'dir_names': None,

            'virtualenv_path': None,

            'flags': None,

            'hidden_columns': 'input_command'
        }

        with open(config_filename, 'w') as f:
            config.write(f)

    def set_defaults(subparser, name):
        assert isinstance(subparser, argparse.ArgumentParser)
        assert isinstance(name, str)

        if name in config:
            subparser.set_defaults(**config[name])

    parser = argparse.ArgumentParser()
    set_defaults(parser, 'DEFAULT')
    subparsers = parser.add_subparsers(dest='dest')
    virtualenv_path_help = 'Path to virtual environment, if one is being ' \
                           'used. If not `None`, the program will source ' \
                           '`<virtualenv-path>/bin/activate`.'
    path_clarification = ' Can be a relative path from runs: `DIR/NAME|PATTERN` Can also be a pattern. '

    new_parser = subparsers.add_parser(NEW, help='Start a new run.')
    new_parser.add_argument(NAME, help='Unique name assigned to new run.' + path_clarification)
    new_parser.add_argument('command', help='Command to run to start tensorflow program. Do not include the `--tb-dir` '
                                            'or `--save-path` flag in this argument')
    new_parser.add_argument('--virtualenv-path', default=None, help=virtualenv_path_help)
    new_parser.add_argument('--no-overwrite', action='store_true', help='Check before overwriting existing runs.')
    new_parser.add_argument('--ignore-dirty', action='store_true', help='Create new run even if repo is dirty.'
                                                                        'overwrite any entry with the same name. ')
    new_parser.add_argument('--description', help='Description of this run. Write whatever you want.')
    new_parser.add_argument('--quiet', '-q', action='store_true', help='Suppress print ouput')
    set_defaults(new_parser, NEW)
    if NEW in config:
        new_parser.set_defaults(**{
            k: v for k, v in config[NEW] if k.endswith('-flag')})

    remove_parser = subparsers.add_parser(REMOVE,
                                          help="Delete runs from the database (and all associated tensorboard "
                                               "and checkpoint files). Don't worry, the script will ask for "
                                               "confirmation before deleting anything.")
    remove_parser.add_argument(PATTERN, default='*',
                               help='This script will only delete entries in the database whose names are a '
                                    'complete (not partial) match of this regex pattern.')
    set_defaults(remove_parser, REMOVE)

    move_parser = subparsers.add_parser(MOVE, help='Move a run from OLD to NEW.')
    move_parser.add_argument('old', help='Name of run to rename.' + path_clarification)
    move_parser.add_argument('new', help='New name for run.' + path_clarification)
    move_parser.add_argument('--' + PATTERN, action='store_true',
                             help='Whether to do a bulk move, interpreting OLD as a pattern')
    move_parser.add_argument('--keep-tmux', action='store_true',
                             help='Rename tmux session instead of killing it.')
    set_defaults(move_parser, MOVE)

    pattern_help = 'Only display names matching this pattern.'
    list_parser = subparsers.add_parser(LIST, help='List all names in run database.')
    list_parser.add_argument(PATTERN, nargs='?', default=None, help=pattern_help)
    set_defaults(list_parser, LIST)

    table_parser = subparsers.add_parser(TABLE, help='Display contents of run database as a table.')
    table_parser.add_argument(PATTERN, nargs='?', default=None, help=pattern_help)
    table_parser.add_argument('--hidden-columns',
                              help='Comma-separated list of columns to not display in table.')
    table_parser.add_argument('--column-width', type=int, default=100,
                              help='Maximum width of table columns. Longer values will '
                                   'be truncated and appended with "...".')
    set_defaults(table_parser, TABLE)

    lookup_parser = subparsers.add_parser(LOOKUP, help='Lookup specific value associated with database entry')
    lookup_parser.add_argument('key', help='Key that value is associated with. To view all available keys, '
                                           'use `--key=None`.')
    lookup_parser.add_argument(PATTERN, help='Pattern of runs for which to retrieve key.')
    lookup_parser.add_argument('--quiet', '-q', action='store_true', help='Suppress any explanatory output.')
    set_defaults(lookup_parser, LOOKUP)

    chdesc_parser = subparsers.add_parser(CHDESCRIPTION, help='Edit description of run.')
    chdesc_parser.add_argument(NAME, help='Name of run whose description you want to edit.')
    set_defaults(chdesc_parser, CHDESCRIPTION)

    reproduce_parser = subparsers.add_parser(REPRODUCE, help='Print commands to reproduce a run.')
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
    set_defaults(reproduce_parser, REPRODUCE)
    args = parser.parse_args(args=argv)
    DBPath.cfg = Cfg(**config['DEFAULT'])

    if args.dest == NEW:
        Run(args.name).start(
            command=args.command,
            description=args.description,
            no_overwrite=args.no_overwrite,
            quiet=args.quiet)

    elif args.dest == REMOVE:
        Pattern(args.pattern).remove()

    elif args.dest == MOVE:
        Pattern(args.old).move(Run(args.new), args.keep_tmux)

    elif args.dest == LIST:
        print_tree(Pattern(args.pattern).tree())

    elif args.dest == TABLE:
        print(Pattern(args.pattern).table(args.column_width))

    elif args.dest == LOOKUP:
        pattern = Pattern(args.pattern)
        for run, value in zip(pattern.runs(), pattern.lookup(args.key)):
            print("{}: {}".format(run.path, value))

    elif args.dest == CHDESCRIPTION:
        Run(args.name).chdescription()

    elif args.dest == REPRODUCE:
        print(Run(args.name).reproduce())

    else:
        raise RuntimeError("'{}' is not a supported dest.".format(args.dest))


if __name__ == '__main__':
    main()
