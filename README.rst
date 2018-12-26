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
* Automatically set up runs, building args and directories with unique name corresponding to each run and launching runs in tmux.
* Organize runs into hierarchical categories.
* Synchronize runs with directories, so that directories are moved and deleted when runs are moved and deleted.

Installation
------------
The only external dependencies of this tool are ``tmux`` and ``git``. After that, ``pip install lab-notebook``.

Usage
-----
Please reference the `ipython notebook demo
<https://github.com/lobachevzky/lab-notebook/blob/master/demo/Demo.ipynb>`_, which reviews the features.

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
