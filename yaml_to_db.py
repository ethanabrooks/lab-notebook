import argparse
from pprint import pprint

import yaml
from pathlib import Path, PurePath

import runs
from runs.commands import table
from runs.database import RunEntry, DataBase
from runs.logger import Logger


def yaml_to_run_entry(node, *parts):
    parts += (node['name'],)
    try:
        for child in node['children']:
            for run in yaml_to_run_entry(child, *parts):
                yield run
    except KeyError:
        yield RunEntry(path=PurePath(*parts),
                       full_command=node['full_command'],
                       commit=node['commit'],
                       datetime=node['datetime'],
                       description=node['description'],
                       input_command=node['_input_command'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('yaml_file', help='input file', type=str)
    parser.add_argument('db_file', nargs='?', default='runs.db',
                        help='output file', type=str)
    parser.add_argument('--column-width', default=100, help='output file', type=int)

    args = parser.parse_args()
    with Path(args.yaml_file).open() as f:
        data = yaml.load(f)

    with DataBase(args.db_file, Logger(quiet=False)) as db:
        for run in yaml_to_run_entry(data):
            db.append(run)

        print(table.string(db))
