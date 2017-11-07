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
* Your program accepts a ``--tb-dir`` flag pointing to the directory where all tensorboard events are saved and a ``--save-path`` flag pointing to the directory where model checkpoints are saved.



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

Example command:

.. code-block:: console

    runs new 'run-name' 'python main.py' --description='Description of program'

``delete``
~~~~~~~~~~
Delete all runs matching pattern. This command also deletes associated tensorboard and checkpoint files.

Example command:

.. code-block:: console

    runs delete 'run-.*'

``list``
~~~~~~~~
List all runs matching pattern.

Example command:

.. code-block:: console

    runs list --pattern='run-.*'

``table``
~~~~~~~~~
Display entries in run-database in table form.

Example command:

.. code-block:: console

    runs table

To filter by regex, use ``--pattern`` flag.

``lookup``
~~~~~~~~~~
Lookup specific value associated with database entry.

Example command:

.. code-block:: console

    runs lookup run-name command  # lookup the command used for 'run-name

``reproduce``
~~~~~~~~~~~~~
Print out commands for reproducing run.

Example command:

.. code-block:: console

    ❯ runs reproduce tester
    To reproduce:
     git checkout 5c9f67d2ad0b08a58f5806d91978096c6adefac9
     runs new tester 'python train.py --geofence=.5 --timesteps-per-batch=256 --ent-coeff=0.1' --description='tester'

