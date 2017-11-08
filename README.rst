Tensorflow Run Manager
======================

Machine learning engineers often run multiple versions of an algorithm concurrently. However, this can make keeping track of and reproducing runs difficult. This simple utility solves this problem by maintaining a database in human-readable YAML formal that tracks

* A unique name assigned to each run.
* A description of each run.
* The exact command used for the run.
* The date and time of the run.
* The most recent commit before the run.

Installation
------------
The only external prerequisites of this tool are ``tmux`` and ``git``. After that, ``pip install run-manager``.

Important paths and files
-------------------------
When you run ``runs new``, the utility automatically creates the following directory structure:

.. code-block:: console

  <Runs Directory>/
      <Runs Database>
      checkpoints/
      tensorboard/<Run Name>/

Runs Database
~~~~~~~~~~~~~
YAML file that stores historical information about Tensorflow runs.

Run Name
~~~~~~~~
This is a unique value that you assign to each run. The ``runs`` section explains how the program deals with collisions.

``checkpoints`` directory
~~~~~~~~~~~~~~~~~~~~~~~~~
Directory where model checkpoints are saved. Used in ``tf.train.Saver().save(sess, <checkpoints directory>/<Run Name>.ckpt)``.

``tensorboard`` directory
~~~~~~~~~~~~~~~~~~~~~~~~~
Directory where events are saved. Used in ``tf.summary.FileWriter(<tensorboard directory>/<Run Name>/)``.

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
===================  ===============  ======================================================================================================================================================

The program expects to find the ``.runsrc`` in the current working directory. The script should always be run from this directory as all file IO commands use relative paths.

Here is an example ``.runsrc`` file:

.. code-block:: yaml

    runs-dir: .lstm-runs/
    db-filename: lstm-runs.yml
    tb-dir-flag: None
    save-path-flag: -s
    column-width:
    virtualenv-path: /home/ethan/virtualenvs/baselines/
    extra-flags:
      - [goal-log-dir, <runs-dir>/goal-logs/<run-name>.log]

Assumptions
-----------
This program tries to assume as little about your program as possible, while providing useful functionality. These assumptions are as follows:

* You call the ``runs`` command from the same directory every time (all file IO paths are relative).
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
