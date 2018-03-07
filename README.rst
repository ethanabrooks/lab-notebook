Lab Notebook
============
Researchers in computer science often need to compare difference versions of a process and compare the results.
``Lab Notebook`` helps document, track, and organize process runs.
This is essential for reproducibility of runs and helps researchers figure out what changes in code led to different outcomes.
The goals of ``Lab Notebook`` are reproducibility, modularity, and organization.
 Specifically, ``Lab Notebook`` provides the following functionality:

* Maintain metadata about each run, including a description, a timestamp, and a git commit.
* Auto-create flags and directories with unique name corresponding to each run
* Organize runs into hierarchical categories.
* Synchronize runs with directories, so that directories are moved and deleted when runs are moved and deleted.
* Ensure that directories are synced with each run, so that if a run is removed from the database or moved into a

Installation
------------
The only external dependencies of this tool are ``tmux`` and ``git``. After that, ``pip install lab-notebook``.

Configuration
-------------
The program will default to any arguments specified in ``.runsrc``.
The user can always override the ``.runsrc`` file with command-line arguments.
For descriptions of arguments, use ``runs -h`` or ``runs [command] -h``
The program searched for the ``.runsrc`` file in ancestors (inclusive) of the current working directory.
If the program does not find a ``.runsrc`` file, it will create one with default values in the current working direcoty.
The user can use three keyword in the ``.runsrc``:

* ``path`` will be replaced by the *path* to the run.
Here is an example ``.runsrc`` file:

.. code-block:: ini
    [multi]
    root = /Users/ethan/baselines/.runs
    db_path = /Users/ethan/baselines/runs.yml
    dir_names = tensorboard
    virtualenv_path = /Users/ethan/virtualenvs/baselines

    [flags]
    --logdir=${multi:root}/tensorboard/<path>

    [new]
    description = demo lab-notebook

Note that ``${multi:root}`` will be replaced by ``/Users/ethan/baselines/.runs`` and

Important paths and files
-------------------------
When you run ``runs new``, the utility automatically creates the following directory structure:

.. code-block:: console

  <Runs Database>
  <Runs Directory>/

      checkpoints/
      tensorboard/<Run Name>/

Runs Database
~~~~~~~~~~~~~
YAML file that stores historical information about Tensorflow runs.

Run Name
~~~~~~~~
This is a unique value that you assign to each run. The ``runs`` section explains how the program deals with collisions.

Configuration
-------------
Runs can be extensively configured using command-line arguments, but the following values can also be configured in a ``.runsrc`` file:

===================  ===============  ======================================================================================================================================================
name                 default          description
===================  ===============  ======================================================================================================================================================
``runs-dir``         ``.runs/``       The name to use for your Runs Directory.
``db-filename``      ``.runs.yml``    The name that you choose to save your runs database with.
``tb-dir-flag``      ``--tb-dir``     The flag that gets passed to your program that specifies ``<tensorboard directory>/<Run Name>/``. If ``None``, no flag will be passed to your program.
``save-path-flag``   ``--save-path``  The flag that gets passed to your program that specifies ``<checkpoints directory>/<Run Name>``. If ``None``, no flag will be passed to your program.
``column-width``     ``30``           The default column width for the ``runs table`` command.
``virtualenv-path``  ``None``         The path to your virtual environment directory, if you're using one. Used in the following command: ``Source <virtualenv-path>/bin/activate``.
``extra-flags``      ``[]``           Flag, value pairs for extra, custom flags. The strings ``<runs-dir>`` and ``<run-name>`` will get replaced with the appropriate value.
===================  ===============  ======================================================================================================================================================

The program expects to find the ``.runsrc`` in a parent of the current working directory. Unless specified otherwise, the ``.runs/`` directory will be adjacent to the ``.runsrc`` in the file structure.

Here is an example ``.runsrc`` file:

.. code-block:: yaml

    runs-dir: .lstm-runs/
    db-filename: lstm-runs.yml
    tb-dir-flag: None
    save-path-flag: -s
    column-width: 10
    virtualenv-path: /home/ethan/virtualenvs/baselines/
    extra-flags:
      - [--goal-log-dir, <runs-dir>/goal-logs/<run-name>.log]

Assumptions
-----------
This program tries to assume as little about your program as possible, while providing useful functionality. These assumptions are as follows:

* You call the ``runs`` command from a directory whose parent contains the runs directory.
* Your program lives in a Git repository.
* The Git working tree is not dirty (if it is, the program will throw an informative error).
* Your program accepts a ``--tb-dir`` flag, which your program uses in ``tf.train.Saver().save(sess, <tf-dir>)``, and a ``--save-path`` flag, which your program uses in ``tf.train.Saver().restore(sess, <save-path>)``. If your flags are different and you don't feel like changing them, you can specify the new flag names using command-line arguments (``--tb-dir-flag`` and ``--save-path-flag``) or in your ``.runsrc`` (see the `Configuration`_ section for more info). If you don't want to pass either flag to your program, set ``--tb-dir-flag`` or ``--save-path-flag`` (or the associated values in your ``.runsrc``) to `None`.


Subcommands
-----------
For detailed descriptions of each subcommand and its arguments, run

.. code-block:: console

  runs <subcommand> -h

``new``
~~~~~~~
Start a new run and build the file structure (see `Important paths and files`_).

It will add an entry to the database keyed by name, with the following values:

* command
* commit
* datetime
* description
* host

Finally, it will execute the command in ``tmux``.

.. code-block:: console

    runs new 'run-name' 'python main.py' --description='Description of program'

*Note:* the ``--tb-dir`` and ``--save-path`` flags will be automatically
appended to this command argument, so do not include them in the ``<command>``
argument.

``delete``
~~~~~~~~~~
Delete all runs matching pattern. This command also deletes associated tensorboard and checkpoint files.

.. code-block:: console

  ❯ runs delete "continuous.*"
  Delete the following runs?
  continuous0
  continuous1
  continuous21509805012
  continuous2
  continuous11509804959
  continuous3
  continuous31509805040

``list``
~~~~~~~~
List all runs matching pattern.

.. code-block:: console

  ❯ runs list --pattern="continuous.*"
  continuous21509805012
  continuous0
  continuous11509804959
  continuous31509805040
  continuous1
  continuous2
  continuous3

``table``
~~~~~~~~~
Display entries in run-database in table form.

.. code-block:: console

  ❯ runs table
  name                           command                            commit                             datetime                    description                          host
  -----------------------------  ---------------------------------  ---------------------------------  --------------------------  ---------------------------------  ------
  continuous2                    CUDA_VISIBLE_DEVICES=1 python ...  90c0ad704e54d5152d897a4e978cc7...  2017-11-03T13:46:48.633364  Run multiple runs to test stoc...    rldl3
  continuous3                    CUDA_VISIBLE_DEVICES=1 python ...  90c0ad704e54d5152d897a4e978cc7...  2017-11-03T13:47:09.951233  Run multiple runs to test stoc...    _
  continuous1                    CUDA_VISIBLE_DEVICES=1 python ...  90c0ad704e54d5152d897a4e978cc7...  2017-11-03T13:42:39.879031  Run multiple runs to test stoc...    _
  house-cnn-no-current-pos       python train.py --timesteps-pe...  9fb9b5a                            2017-10-28T18:07:44.246089  This is the refactored CNN on ...    _
  room-with-original-cnn         python run_custom.py --timeste...  8a5e1c2                            2017-10-28T17:09:49.971061  Test original cnn on room.mjcf       _
  continuous11509804959          CUDA_VISIBLE_DEVICES=1 python ...  90c0ad704e54d5152d897a4e978cc7...  2017-11-04T10:15:59.373633  Run multiple runs to test stoc...    _
  continuous31509805040          CUDA_VISIBLE_DEVICES=1 python ...  90c0ad704e54d5152d897a4e978cc7...  2017-11-04T10:17:20.286275  Run multiple runs to test stoc...    rldl4
  room-cnn-no-current-pos        python train.py --timesteps-pe...  2873fbf                            2017-10-28T18:08:10.615461  This is the refactored CNN on ...    rldl4
  continuous21509805012          CUDA_VISIBLE_DEVICES=1 python ...  90c0ad704e54d5152d897a4e978cc7...  2017-11-04T10:16:52.129656  Run multiple runs to test stoc...    _


To filter by regex, use ``--pattern`` flag.

``lookup``
~~~~~~~~~~
Lookup specific value associated with database entry.

.. code-block:: console

  ❯ runs lookup continuous0 commit
  da6030dd973c810c330d9635eb8d9c2105bdfe2f

``reproduce``
~~~~~~~~~~~~~
Print out commands for reproducing run.

.. code-block:: console

  ❯ runs reproduce continuous0    
  To reproduce:
   git checkout da6030dd973c810c330d9635eb8d9c2105bdfe2f
   runs new continuous0 'python run_custom.py --timesteps-per-batch=2048 --continuous-actions --neg-reward --use-cnn' --description='None'

Why not just use git?
=====================

* If processes are long-running, it is hard to know which commit a given run corresponds to.
* Commit statements are really meant to describe *changes* to software, not *runs*. A description of a change may not actually tell you very much about the motivation for a software run.
* Not all commits will correspond to runs, so you will need to fish through a large number of commits to find those that correspond to runs.
* Often processes depend on specific file-structures (e.g. a logging directory). Setting up and removing these directories by hand is time-consuming and error-prone.
* Commits cannot be organized hierarchically or categorized after their creation.
