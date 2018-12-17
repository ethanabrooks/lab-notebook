# stdlib
import argparse
from pathlib import Path, PurePath
import pickle

# third party
import yaml

# first party
from runs.commands import ls
from runs.database import DataBase
from runs.logger import Logger
from runs.run_entry import RunEntry


def yaml_to_run_entry(node, *parts):
    parts += (node['name'], )
    try:
        for child in node['children']:
            for run in yaml_to_run_entry(child, *parts):
                yield run
    except KeyError:
        yield RunEntry(
            path=PurePath(*parts),
            command=node['command'],
            commit=node['commit'],
            datetime=node['datetime'],
            description=node['description'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('yaml_file', help='input file', type=str)
    parser.add_argument(
        'db_file', nargs='?', default='runs.db', help='output file', type=str)
    parser.add_argument('--column-width', default=100, help='output file', type=int)

    args = parser.parse_args()
    if args.yaml_file.endswith('yml') or args.yaml_file.endswith('yaml'):
        with Path(args.yaml_file).open() as f:
            data = yaml.load(f)
    elif args.yaml_file.endswith('pkl'):
        with Path(args.yaml_file).open('rb') as f:
            data = pickle.load(f)
    else:
        raise RuntimeError('This script works on yaml or pickle files only')

    with DataBase(args.db_file, Logger(quiet=False)) as db:
        for run in yaml_to_run_entry(data):
            db.append(run)

        print(ls.string(db=db))


if __name__ == '__main__':
    main()
