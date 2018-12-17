.. image:: https://travis-ci.org/lobachevzky/lab-notebook.svg?branch=master
    :target: https://travis-ci.org/lobachevzky/lab-notebook
    
Lab Notebook
============
Researchers in computer science often need to compare results between different versions of a process.
``Lab Notebook`` helps document, track, and organize process these kinds of runs.
This is essential for reproducibility and helps researchers figure out what changes in code led to different outcomes.
The goals of ``Lab Notebook`` are reproducibility, modularity, and organization.
Specifically, ``Lab Notebook`` provides the following functionality:

* Maintain metadata about each run, including a description, a timestamp, and a git commit.
* Automatically set up runs, building flags and directories with unique name corresponding to each run and launching runs in tmux.
* Organize runs into hierarchical categories.
* Synchronize runs with directories, so that directories are moved and deleted when runs are moved and deleted.

Installation
------------
The only external dependencies of this tool are ``tmux`` and ``git``. After that, ``pip install lab-notebook``.

Configuration
-------------
The program will default to any arguments specified in ``.runsrc``.
The user can always override the ``.runsrc`` file with command-line arguments.
For descriptions of arguments, use ``runs -h`` or ``runs [command] -h``
The program searches for the ``.runsrc`` file in ancestors (inclusive) of the current working directory.
If the program does not find a ``.runsrc`` file, it will create one with default values in the current working directory.
The user can use two keyword in the ``.runsrc``:

* ``<path>`` will be replaced by the *path* to the run. Paths look just like ordinary file paths (``/``-delimited).
* ``<name>`` will be replaced by the head of *path*.

Also users can interpolate strings from other sections of ``.runsrc`` using the syntax ``${section:value}``.
For more details see
`configparser ExtendedInterpolation <https://docs.python.org/3/library/configparser.html#configparser.ExtendedInterpolation>`_.

Here is an example ``.runsrc`` file:

.. code-block:: ini

    [main]
    root = /Users/ethan/demo-lab-notebook/.runs
    db_path = /Users/ethan/demo-lab-notebook/runs.pkl
    dir_names = tensorboard
    prefix = Source ~/virtualenvs/demo-lab-notebook/bin/activate;
    nice

    [flags]
    --log-dir=${main:root}/tensorboard/<path>

    [new]
    description = demo lab-notebook

This will pass the flag ``--logdir=/Users/ethan/baselines/.runs/tensorboard/<path>``
to any program launched with ``run``, where ``<path>`` will be replaced by the ``path`` argument given by the user.

``runs-git``
------------
This is a simple wrapper around ``git`` that substitutes ``+your-path`` with ``runs lookup commit your-path``.
For example, to see changes since when you launched ``your-run``:

.. code-block:: console

  runs-git diff +your-run

If you want to live on the wild side, use `direnv <https://direnv.net/>`_ to alias ``git`` to ``runs-git`` when you
are in your project directory.

Example Usage
-------------
Setup environment:

.. code-block:: console

  mkdir ~/lab-notebook-demo/ && cd ~/lab-notebook-demo
  wget https://raw.githubusercontent.com/tensorflow/tensorflow/master/tensorflow/examples/tutorials/mnist/mnist_with_summaries.py
  pip install tensorflow lab-notebook
  git init
  echo 'runs.pkl .runs .runsrc' > .gitignore
  git add -A
  git commit -am init

Create a new run. The run will be launched in ``tmux``:

.. code-block:: console

  runs new train 'python mnist_with_summaries.py' --description='demo new command'

Check out your run:

.. code-block:: console

  tmux attach -t train

Reproduce your run:

.. code-block:: console

  runs reproduce train
  runs reproduce --no-overwrite train

Try modifying the ``.runsrc`` file to look like the example in the
`Configuration`_ section with appropriate changes for your system.
Then create a new run:

.. code-block:: console

  runs new subdir/train 'python mnist_with_summaries.py' --description='demo categorization'

Get an overview of what runs are in the database:

.. code-block:: console

  runs ls
  runs ls 'tra*'
  runs ls --show-attrs

Query information about current runs:

.. code-block:: console

  runs lookup description train
  runs lookup commit train

``runs-git``: avoid typing ``runs lookup commit <path>`` all the time:

.. code-block:: console

  echo '# Hello' >> mnist_with_summaries.py
  runs-git diff +train

Organize runs

.. code-block:: console

  runs mv train subdir/train2
  runs ls
  tree .runs  # note that directories are synchronized with database entries
  runs mv subdir archive
  runs ls

Delete runs

.. code-block:: console

  runs rm archive/train
  runs killall


Subcommands
-----------
For an overview of subcommands, run

.. code-block:: console

  runs -h

For detailed descriptions of each subcommand and its arguments, run

.. code-block:: console

  runs <subcommand> -h

Tab autocompletion
------------------
If you are using Zsh, simpy copy the ``_runs`` to some place on your ``fpath``.
Then pressing tab will prompt you with the names of runs currently in your
database

Why not just use git?
---------------------
* If processes are long-running, it is hard to know which commit a given run corresponds to.
* Commit statements are really meant to describe *changes* to software, not *runs*. A description of a change may not actually tell you very much about the motivation for a software run.
* Not all commits will correspond to runs, so you will need to fish through a large number of commits to find those that correspond to runs.
* Often processes depend on specific file-structures (e.g. a logging directory). Setting up and removing these directories by hand is time-consuming and error-prone.
* Commits cannot be organized hierarchically or categorized after their creation.
