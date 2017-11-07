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

Assumptions
-----------
This program tries to assume as little about your program as possible, while providing useful functionality. These assumptions are as follows:

* Your program lives in a Git repository.
* The Git working tree is not dirty (if it is, the program will throw an informative error).
* Your program accepts two flags:

  - ``--tb-dir``: pointing to the same directory that you would specify in ``tensorboard logdir=<tb-dir>`` .
  - ``--save-path``: pointing to the directory of the file that you would pass to ``tf.train.Saver().restore(sess, <save-path>)``.



Subcommands
-----------
For detailed descriptions of each subcommand and its arguments, run

.. code-block:: console

  runs <subcommand> -h

``new``
~~~~~~~
Start a new run. This command will automatically create the file structure:

.. code-block:: console

  <runs-dir>/
      <db-filename>
      checkpoints/
      tensorboard/<run-name>/

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
