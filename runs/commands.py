import os
import shutil
from datetime import datetime

from tabulate import tabulate

from runs.util import highlight, load, RunDB, get_yes_or_no, run_dirs, run_paths, make_dirs, cmd, run_tmux, kill_tmux, \
    rename_tmux, no_match, NAME, INPUT_COMMAND, COMMAND, COMMIT, DATETIME, \
    DESCRIPTION, string_from_vim


def build_flags(name, runs_dir, tb_dir_flag, save_path_flag, extra_flags):
    tb_dir, save_path = run_paths(runs_dir, name)
    flags = [(tb_dir_flag, tb_dir), (save_path_flag, save_path)]
    for flag, value in extra_flags:
        value = value.replace('<run-name>', name).replace('<runs-dir>', runs_dir)
        flags += [(flag, value)]

    return ' '.join(['{}={}'.format(flag, value)
                     for flag, value in flags
                     if flag is not None])


def build_command(command, name, runs_dir, virtualenv_path, tb_dir_flag, save_path_flag, extra_flags):
    command += ' ' + build_flags(name, runs_dir, tb_dir_flag, save_path_flag, extra_flags)
    if virtualenv_path:
        return 'source ' + virtualenv_path + '/bin/activate; ' + command
    return command


def new(name, command, description, virtualenv_path, overwrite, runs_dir, db_filename,
        tb_dir_flag, save_path_flag, extra_flags):
    for char in '.&':
        assert char not in name, 'run name cannot include "{}"'.format(char)
    now = datetime.now()

    # deal with collisions
    db_path = os.path.join(runs_dir, db_filename)
    if name in load(db_path):
        if overwrite:
            delete_run(name, db_filename, runs_dir)
        else:
            name += now.strftime('%s')

    make_dirs(runs_dir, name)
    if cmd('git status --porcelain') is not '':
        if not get_yes_or_no("Repo is dirty. You should commit before run. Run anyway?"):
            exit()

    processed_command = build_command(command, name, runs_dir, virtualenv_path,
                                      tb_dir_flag, save_path_flag, extra_flags)

    if description is None:
        description = cmd('git log -1 --pretty=%B')

    last_commit_hex = cmd('git rev-parse HEAD')
    prompt = 'Edit the description of this run: (Do not edit the line or above.)'
    description = string_from_vim(prompt, description)
    entry = {
        INPUT_COMMAND: command,
        COMMAND: processed_command,
        COMMIT: last_commit_hex,
        DATETIME: now.isoformat(),
        DESCRIPTION: description,
    }

    with RunDB(path=db_path) as db:
        db[name] = entry

    run_tmux(name, description, processed_command)

    print(highlight('Description:'))
    print(description)
    print(highlight('Command sent to session:'))
    print(processed_command)
    print(highlight('List active:'))
    print('tmux list-session')
    print(highlight('Attach:'))
    print('tmux attach -t', name)


def bulk_move(run_names, old_runs_dir, new_runs_dir, db_filename, _kill_tmux):
    if run_names:
        question = 'Move the following runs from {} to {}?\n'.format(
            old_runs_dir, new_runs_dir) + '\n' + '\n'.join(run_names) + '\n'
        if get_yes_or_no(question):
            for run_name in run_names:
                move(old_runs_dir, run_name, new_runs_dir, run_name,
                     db_filename, _kill_tmux)
                print('Moved', run_name, 'from', old_runs_dir, 'to', new_runs_dir)
    else:
        no_match(old_runs_dir, db_filename)


def move(old_runs_dir, old_name, new_runs_dir, new_name, db_filename, _kill_tmux):
    make_dirs(new_runs_dir, new_name)
    old_db_path = os.path.join(old_runs_dir, db_filename)
    new_db_path = os.path.join(new_runs_dir, db_filename)
    with RunDB(path=old_db_path) as old_db, RunDB(path=new_db_path) as new_db:
        new_db[new_name] = old_db[old_name]
        del old_db[old_name]
        for old_dir, new_dir in zip(run_dirs(old_runs_dir, old_name),
                                    run_dirs(new_runs_dir, new_name)):
            os.rename(old_dir, new_dir)

    if _kill_tmux:
        rename_tmux(old_name, new_name)
    else:
        kill_tmux(old_name)


def delete(run_names, db_filename, runs_dir):
    if run_names:
        question = 'Delete the following runs?\n' + '\n'.join(run_names) + '\n'
        if get_yes_or_no(question):
            for run_name in run_names:
                delete_run(run_name, db_filename, runs_dir)
                print('Deleted', run_name)
    else:
        no_match(runs_dir, db_filename)


def delete_run(name, db_filename, runs_dir):
    print('Deleting {}...'.format(name))
    with RunDB(path=(os.path.join(runs_dir, db_filename))) as db:
        del db[name]
        for run_dir in run_dirs(runs_dir, name):
            shutil.rmtree(run_dir)

    kill_tmux(name)


def lookup(db, name, key):
    documented_runs_message = "Documented runs are {}.".format(name, db.keys())
    if key is None:
        return documented_runs_message
    if name not in db.keys():
        raise KeyError(
            "`{}` is not a documented run.".format(name) + documented_runs_message)
    entry = db[name]
    if key not in entry:
        raise KeyError(
            "`{}` not a valid key. Valid keys are {}.".format(
                key, entry.keys()))
    return entry[key]


def get_table(db, column_width, hidden_columns):
    def get_values(entry, key):
        try:
            value = str(entry[key])
            if len(value) > column_width:
                value = value[:column_width] + '...'
            return value
        except KeyError:
            return '_'

    all_keys = (key for _, entry in db.items() for key in entry)
    headers = sorted(set(all_keys) - set(hidden_columns))
    table = [[name] + [get_values(entry, key) for key in headers]
             for name, entry in sorted(db.items())]
    headers = [NAME] + list(headers)
    return tabulate(table, headers=headers)


def load_table(runs_dir, db_filename, run_names, host,
               column_width, username, hidden_columns):
    db = load(os.path.join(runs_dir, db_filename), host, username)
    filtered = {k: v for k, v in db.items() if k in run_names}
    return get_table(filtered, column_width, hidden_columns)


def reproduce(runs_dir, db_filename, name):
    db = load(os.path.join(runs_dir, db_filename))
    commit = lookup(db, name, key=COMMIT)
    command = lookup(db, name, key=INPUT_COMMAND)
    description = lookup(db, name, key=DESCRIPTION)
    print('To reproduce:\n',
          highlight('git checkout {}\n'.format(commit)),
          highlight("runs new {} '{}' --description='{}'".format(
              name, command, description)))
